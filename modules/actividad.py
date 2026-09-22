"""
Módulo Actividad Clínica — Unifica Profesionales + Citas
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.db_connector import get_db_connector
from utils.queries import SIHOSQueries, dataframe_to_excel
from config.settings import COLORS, CACHE_TTL
from components.widgets import (
    get_fecha_rango_texto, render_metric_card,
    render_section_banner, render_section_divider,
    render_heading_help
)
from components.layout import render_footer


def render_actividad():
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio',
                                        datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)

    render_section_banner("👨‍⚕️", "Actividad Clínica — Profesionales y Citas", rango_fechas)

    tab_prof, tab_citas = st.tabs(["👨‍⚕️ Profesionales", "📅 Citas"])

    with tab_prof:
        _render_profesionales(fecha_inicio, fecha_fin, rango_fechas)

    with tab_citas:
        _render_citas(fecha_inicio, fecha_fin, rango_fechas)

    render_footer()


def _render_profesionales(fecha_inicio, fecha_fin, rango_fechas):
    @st.cache_data(ttl=CACHE_TTL)
    def load(f_ini, f_fin):
        db = get_db_connector()
        q = SIHOSQueries()
        params = {'fecha_inicio': f_ini, 'fecha_fin': f_fin}
        return {
            'estadisticas':      db.execute_query(q.get_estadisticas_profesionales(), params),
            'por_modulo':        db.execute_query(q.get_atenciones_por_modulo(), params),
            'por_ambito':        db.execute_query(q.get_profesionales_por_ambito(), params),
            'top_profesionales': db.execute_query(q.get_top_profesionales(), params),
            'heatmap_hora':      db.execute_query(q.get_heatmap_hora_profesional(), params),
        }

    data = load(fecha_inicio, fecha_fin)

    # KPIs
    if not data['estadisticas'].empty:
        s = data['estadisticas'].iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_metric_card("👥", "PROFESIONALES ACTIVOS",
                f"{int(s.get('Profesionales_Activos', 0)):,}",
                COLORS['primary'], COLORS['secondary'],
                help_text="Usuarios (RipsCons.UsuaCons) distintos con al menos una atención en el período.")
        with col2:
            render_metric_card("📋", "TOTAL ATENCIONES",
                f"{int(s.get('Total_Atenciones', 0)):,}",
                COLORS['info'], COLORS['primary'],
                help_text="Registros de RipsCons con fecha en el rango seleccionado.")
        with col3:
            render_metric_card("✅", "REALIZADAS",
                f"{int(s.get('Atenciones_Realizadas', 0)):,}",
                COLORS['success'], COLORS['info'],
                help_text="EstaReal=1 — la atención quedó efectivamente registrada como realizada.")
        with col4:
            render_metric_card("⏳", "PENDIENTES",
                f"{int(s.get('Atenciones_Pendientes', 0)):,}",
                COLORS['warning'], COLORS['danger'],
                help_text="EstaReal=0 — atención registrada pero aún no marcada como realizada.")

    render_section_divider()

    # Distribución por ámbito y módulo
    render_section_banner("🏥", "Atenciones por Ámbito y Módulo Clínico", rango_fechas)

    col_amb, col_mod = st.columns(2)

    with col_amb:
        if not data['por_ambito'].empty:
            fig = px.bar(
                data['por_ambito'],
                x='TotalAtenciones',
                y='Ambito',
                orientation='h',
                color='Ambito',
                title='Por ámbito (ambulatorio vs hospitalario)',
                text='TotalAtenciones'
            )
            fig.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig.update_layout(
                height=350,
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_mod:
        if not data['por_modulo'].empty:
            fig2 = px.bar(
                data['por_modulo'],
                x='Total_Atenciones',
                y='Modulo',
                orientation='h',
                color='PctCumplimiento',
                color_continuous_scale='RdYlGn',
                title='Por módulo clínico (color = % cumplimiento)',
                text='Total_Atenciones'
            )
            fig2.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig2.update_layout(
                height=350,
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

    render_section_divider()

    # Top profesionales
    render_section_banner("🏆", "Top Profesionales por Atenciones", rango_fechas)

    if not data['top_profesionales'].empty:
        top_n = st.slider("Cantidad:", 5, 30, 15, key="act_top_prof")
        df_top = data['top_profesionales'].head(top_n)

        fig_top = px.bar(
            df_top, x='Total_Atenciones', y='Profesional',
            orientation='h', color='Total_Atenciones',
            color_continuous_scale='Blues',
            title=f"Top {top_n} Profesionales"
        )
        fig_top.update_layout(
            height=max(400, top_n * 30),
            yaxis={'categoryorder': 'total ascending'},
            showlegend=False
        )
        st.plotly_chart(fig_top, use_container_width=True)

        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(df_top, use_container_width=True, hide_index=True)
            st.download_button("📥 Descargar CSV",
                df_top.to_csv(index=False, encoding='utf-8-sig'),
                f"profesionales_{fecha_inicio}_{fecha_fin}.csv", mime="text/csv")
            st.download_button("📥 Descargar Excel",
                dataframe_to_excel(df_top),
                f"profesionales_{fecha_inicio}_{fecha_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    render_section_divider()

    # Heatmap
    render_section_banner(
        "🌡️", "Mapa de Calor — Carga Horaria", rango_fechas,
        help_text="Las celdas más oscuras indican mayor concentración de atenciones. "
                  "Útil para planificación de turnos y recursos."
    )

    if not data['heatmap_hora'].empty:
        df_heat = data['heatmap_hora'].copy()
        orden_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
        pivot = df_heat.pivot_table(
            index='Hora', columns='NombreDia',
            values='Total', aggfunc='sum', fill_value=0
        )
        dias_presentes = [d for d in orden_dias if d in pivot.columns]
        pivot = pivot[dias_presentes]
        fig_heat = px.imshow(
            pivot, labels=dict(x="Día", y="Hora", color="Atenciones"),
            title="Intensidad de atenciones por hora y día",
            color_continuous_scale='Blues', aspect='auto'
        )
        fig_heat.update_layout(height=500)
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No hay datos de horario de atenciones para el período seleccionado.")

    render_section_divider()

    # ── Producción individual por profesional ──────────────────────────────
    render_section_banner("📋", "Producción Individual por Profesional", rango_fechas)

    db = get_db_connector()
    queries = SIHOSQueries()

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])

    with col_f2:
        prod_ini = st.date_input(
            "Desde",
            value=date(date.today().year, date.today().month, 1),
            key="prod_fecha_ini"
        )
    with col_f3:
        prod_fin = st.date_input(
            "Hasta",
            value=date.today(),
            key="prod_fecha_fin"
        )

    with col_f1:
        with st.spinner("Cargando profesionales..."):
            try:
                df_prof_lista = db.execute_query(
                    queries.get_profesionales_lista(),
                    {"fecha_inicio": str(prod_ini), "fecha_fin": str(prod_fin)}
                )
                # Corrección encoding latin1→utf-8 si aplica
                for col in ['nombre', 'especialidad']:
                    if col in df_prof_lista.columns:
                        def _fix_enc(x):
                            try:
                                return x.encode('latin1').decode('utf-8') if isinstance(x, str) else x
                            except Exception:
                                return x
                        df_prof_lista[col] = df_prof_lista[col].apply(_fix_enc)
                prof_ok = True
            except Exception as e:
                st.error(f"Error cargando profesionales: {e}")
                prof_ok = False

        if prof_ok and not df_prof_lista.empty:
            opciones = {
                f"{row['nombre']} — {row['especialidad']}": row['login']
                for _, row in df_prof_lista.iterrows()
            }
            prof_sel_label = st.selectbox(
                "Seleccionar profesional",
                options=list(opciones.keys()),
                key="prof_produccion_sel"
            )
            prof_login = opciones[prof_sel_label]
        else:
            st.warning("No hay profesionales con citas en el período seleccionado.")
            prof_login = None

    if prof_login:
        params_prod = {
            "login":        prof_login,
            "fecha_inicio": str(prod_ini),
            "fecha_fin":    str(prod_fin),
        }

        with st.spinner("Cargando producción..."):
            try:
                df_kpis   = db.execute_query(queries.get_produccion_profesional_kpis(), params_prod)
                df_det    = db.execute_query(queries.get_produccion_profesional_detalle(), params_prod)
                df_tend   = db.execute_query(queries.get_produccion_profesional_tendencia(), params_prod)
                df_fina   = db.execute_query(queries.get_produccion_profesional_finalidad(), params_prod)
                prod_ok   = True
            except Exception as e:
                st.error(f"Error cargando producción: {e}")
                prod_ok = False

        if prod_ok and not df_kpis.empty:
            row_k = df_kpis.iloc[0]
            cumplidas      = int(row_k.get('cumplidas', 0) or 0)
            ocupadas       = int(row_k.get('ocupadas', 0) or 0)
            canceladas     = int(row_k.get('canceladas', 0) or 0)
            inasistencias  = int(row_k.get('inasistencias', 0) or 0)
            no_atendidas   = int(row_k.get('no_atendidas', 0) or 0)
            total          = int(row_k.get('total', 0) or 0)
            duracion_prom  = round(float(row_k.get('duracion_prom_min') or 0), 1)
            tasa           = round(cumplidas / total * 100, 1) if total > 0 else 0.0

            # KPIs
            st.markdown(f"#### {prof_sel_label.split(' — ')[0]}")
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("✅ Cumplidas", f"{cumplidas:,}",
                      help="EstaCita=3 — citas de este profesional que se completaron.")
            k2.metric("📅 Pendientes", f"{ocupadas:,}",
                      help="EstaCita=2 (Ocupada) — citas agendadas aún por realizarse.")
            k3.metric("❌ Canceladas", f"{canceladas:,}",
                      help="EstaCita=6 — citas canceladas antes de la fecha programada.")
            k4.metric("🚫 Inasistencias", f"{inasistencias:,}",
                      help="EstaCita=4 (Incumplida - Paciente) — el paciente no se presentó a la cita.")
            k5.metric("⚠️ No atendidas", f"{no_atendidas:,}",
                      help="EstaCita=5 o 7 (Incumplida - Médico / Incumplida - Sistema) — "
                           "la cita no se realizó por causa del profesional o del sistema, no del paciente.")
            k6.metric("📊 % Cumplimiento", f"{tasa}%",
                      delta=f"Prom. {duracion_prom} min/cita",
                      help="Cumplidas / Total de citas del profesional en el período.")

            st.divider()

            col_tend, col_fina = st.columns([3, 1])

            with col_tend:
                st.markdown("#### Tendencia diaria")
                if not df_tend.empty:
                    fig_tend = go.Figure()
                    fig_tend.add_trace(go.Bar(
                        x=df_tend['fecha'], y=df_tend['cumplidas'],
                        name='Cumplidas', marker_color='#4CAF50'
                    ))
                    fig_tend.add_trace(go.Bar(
                        x=df_tend['fecha'], y=df_tend['no_cumplidas'],
                        name='Canceladas/Inasist./No atend.', marker_color='#F44336'
                    ))
                    fig_tend.add_trace(go.Bar(
                        x=df_tend['fecha'], y=df_tend['pendientes'],
                        name='Pendientes', marker_color='#2196F3'
                    ))
                    fig_tend.update_layout(
                        barmode='stack', height=320,
                        legend=dict(orientation='h', yanchor='bottom', y=1.02),
                        xaxis_title='', yaxis_title='Citas',
                        margin=dict(t=40, b=10)
                    )
                    st.plotly_chart(fig_tend, use_container_width=True)
                else:
                    st.info("Sin datos de tendencia para el período.")

            with col_fina:
                st.markdown("#### Por finalidad")
                if not df_fina.empty:
                    fig_fina = px.pie(
                        df_fina, names='finalidad', values='total',
                        hole=0.45, height=320,
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_fina.update_traces(textinfo='percent+label')
                    fig_fina.update_layout(
                        showlegend=False,
                        margin=dict(t=40, b=10, l=10, r=10)
                    )
                    st.plotly_chart(fig_fina, use_container_width=True)
                else:
                    st.info("Sin citas cumplidas.")

            st.divider()

            # Tabla detalle
            st.markdown("#### Detalle de citas")
            estados_disp = ['Todos'] + sorted(df_det['estado'].dropna().unique().tolist())
            estado_filtro = st.selectbox("Filtrar por estado", estados_disp,
                                         key="prod_estado_filtro")
            df_det_filt = df_det if estado_filtro == 'Todos' \
                          else df_det[df_det['estado'] == estado_filtro]

            st.caption(f"{len(df_det_filt):,} registros")
            st.dataframe(df_det_filt, use_container_width=True, hide_index=True)

            import io as _io
            buf = _io.BytesIO()
            df_det_filt.to_excel(buf, index=False, engine='openpyxl')
            buf.seek(0)
            nombre_archivo = prof_sel_label.split(' — ')[0].replace(' ', '_')
            st.download_button(
                f"⬇️ Exportar producción — {prof_sel_label.split(' — ')[0]}",
                data=buf,
                file_name=f"produccion_{nombre_archivo}_{prod_ini}_{prod_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


def _render_citas(fecha_inicio, fecha_fin, rango_fechas):
    @st.cache_data(ttl=CACHE_TTL)
    def load(f_ini, f_fin):
        db = get_db_connector()
        q = SIHOSQueries()
        params = {'fecha_inicio': f_ini, 'fecha_fin': f_fin}
        return {
            'estadisticas': db.execute_query(q.get_estadisticas_citas(), params),
            'distribucion': db.execute_query(q.get_distribucion_estado_citas(), params),
            'espera_sol':   db.execute_query(q.get_oportunidad_espera_solicitud(), params),
            'espera_asi':   db.execute_query(q.get_oportunidad_espera_asignacion(), params),
        }

    data = load(fecha_inicio, fecha_fin)

    # KPIs
    if not data['estadisticas'].empty:
        s = data['estadisticas'].iloc[0]
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            render_metric_card("📅", "TOTAL CITAS",
                f"{int(s.get('Total_Citas', 0)):,}",
                COLORS['primary'], COLORS['secondary'],
                help_text="Citas con EstaCita entre 1 y 7 (códigos internos 8-95 excluidos) en el rango.")
        with col2:
            render_metric_card("✅", "CUMPLIDAS",
                f"{int(s.get('Cumplidas', 0)):,}",
                COLORS['success'], COLORS['info'],
                help_text="EstaCita=3 — el paciente asistió y la cita se completó.")
        with col3:
            render_metric_card("📋", "OCUPADAS",
                f"{int(s.get('Ocupadas', 0)):,}",
                COLORS['info'], COLORS['primary'],
                help_text="EstaCita=2 — cita agendada, aún pendiente de realizarse.")
        with col4:
            render_metric_card("⚠️", "INCUMPLIDAS",
                f"{int(s.get('Incumplidas', 0)):,}",
                COLORS['warning'], COLORS['danger'],
                help_text="EstaCita en (4, 5, 7) — el paciente no se presentó o la cita no se completó.")
        with col5:
            render_metric_card("❌", "CANCELADAS",
                f"{int(s.get('Canceladas', 0)):,}",
                COLORS['danger'], COLORS['warning'],
                help_text="EstaCita=6 — cita cancelada antes de la fecha programada.")

    render_section_divider()

    # Distribución
    if not data['distribucion'].empty:
        col_g, col_t = st.columns([2, 1])
        with col_g:
            fig = px.pie(
                data['distribucion'], values='TotalCitas', names='Estado',
                title='Distribución por estado de cita',
                color_discrete_sequence=[
                    COLORS['success'], COLORS['info'], COLORS['warning'],
                    COLORS['danger'], COLORS['primary'], COLORS['secondary'],
                ]
            )
            fig.update_traces(textposition='inside', textinfo='percent+label+value')
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            render_heading_help(
                "Detalle", "Solo estados 1-7. Códigos internos (8-95) excluidos.",
                tag="h4"
            )
            st.dataframe(data['distribucion'], use_container_width=True, hide_index=True)
            st.download_button("📥 CSV",
                data['distribucion'].to_csv(index=False, encoding='utf-8-sig'),
                f"citas_estado_{fecha_inicio}_{fecha_fin}.csv", mime="text/csv")

    render_section_divider()

    # Indicadores de oportunidad
    render_section_banner("⏱️", "Indicadores de Oportunidad de Acceso", rango_fechas)

    col_k1, col_k2 = st.columns(2)

    with col_k1:
        st.markdown("### KPI 1 — Espera desde Solicitud")
        if not data['espera_sol'].empty:
            esp = data['espera_sol'].iloc[0]
            dias = float(esp.get('PromEsperaSolicitud') or 0)
            color = COLORS['danger'] if dias > 15 else COLORS['warning'] if dias > 7 else COLORS['success']
            render_metric_card("📬", "DÍAS PROM. (SOLICITUD)",
                f"{dias:.1f} días", color, COLORS['secondary'],
                help_text="Días entre FechSoli (solicitud) y FechCita. Filtro: FechSoli en el rango seleccionado.")
            st.metric("Citas en muestra", f"{int(esp.get('TotalCitas', 0)):,}",
                      help="Citas usadas para calcular el promedio de este KPI.")
            st.warning("⚠️ Valor (~2.5 días) difiere del SIHOS nativo (29.66 días). Pendiente con Sinergia.")

    with col_k2:
        st.markdown("### KPI 2 — Espera desde Asignación ✅")
        if not data['espera_asi'].empty:
            esp = data['espera_asi'].iloc[0]
            dias = float(esp.get('PromEsperaAsignacion') or 0)
            color = COLORS['danger'] if dias > 15 else COLORS['warning'] if dias > 7 else COLORS['success']
            render_metric_card("📆", "DÍAS PROM. (ASIGNACIÓN)",
                f"{dias:.1f} días", color, COLORS['secondary'],
                help_text="Días entre FechAsig (asignación) y FechCita. Filtro: FechCita en el rango seleccionado.")
            st.metric("Citas en muestra", f"{int(esp.get('TotalCitas', 0)):,}",
                      help="Citas usadas para calcular el promedio de este KPI.")
            st.success("✅ Valor esperado ~8.7 días — validado contra SIHOS nativo (7.92 días).")

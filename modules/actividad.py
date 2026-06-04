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
    render_section_banner, render_section_divider
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
                COLORS['primary'], COLORS['secondary'])
        with col2:
            render_metric_card("📋", "TOTAL ATENCIONES",
                f"{int(s.get('Total_Atenciones', 0)):,}",
                COLORS['info'], COLORS['primary'])
        with col3:
            render_metric_card("✅", "REALIZADAS",
                f"{int(s.get('Atenciones_Realizadas', 0)):,}",
                COLORS['success'], COLORS['info'])
        with col4:
            render_metric_card("⏳", "PENDIENTES",
                f"{int(s.get('Atenciones_Pendientes', 0)):,}",
                COLORS['warning'], COLORS['danger'])

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
    render_section_banner("🌡️", "Mapa de Calor — Carga Horaria", rango_fechas)

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
        st.caption(
            "Las celdas más oscuras indican mayor concentración de atenciones. "
            "Útil para planificación de turnos y recursos."
        )
    else:
        st.info("No hay datos de horario de atenciones para el período seleccionado.")


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
                COLORS['primary'], COLORS['secondary'])
        with col2:
            render_metric_card("✅", "CUMPLIDAS",
                f"{int(s.get('Cumplidas', 0)):,}",
                COLORS['success'], COLORS['info'])
        with col3:
            render_metric_card("📋", "OCUPADAS",
                f"{int(s.get('Ocupadas', 0)):,}",
                COLORS['info'], COLORS['primary'])
        with col4:
            render_metric_card("⚠️", "INCUMPLIDAS",
                f"{int(s.get('Incumplidas', 0)):,}",
                COLORS['warning'], COLORS['danger'])
        with col5:
            render_metric_card("❌", "CANCELADAS",
                f"{int(s.get('Canceladas', 0)):,}",
                COLORS['danger'], COLORS['warning'])

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
            st.markdown("#### Detalle")
            st.dataframe(data['distribucion'], use_container_width=True, hide_index=True)
            st.caption("*Solo estados 1-7. Códigos internos (8-95) excluidos.*")
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
                f"{dias:.1f} días", color, COLORS['secondary'])
            st.metric("Citas en muestra", f"{int(esp.get('TotalCitas', 0)):,}")
            st.warning("⚠️ Valor (~2.5 días) difiere del SIHOS nativo (29.66 días). Pendiente con Sinergia.")

    with col_k2:
        st.markdown("### KPI 2 — Espera desde Asignación ✅")
        if not data['espera_asi'].empty:
            esp = data['espera_asi'].iloc[0]
            dias = float(esp.get('PromEsperaAsignacion') or 0)
            color = COLORS['danger'] if dias > 15 else COLORS['warning'] if dias > 7 else COLORS['success']
            render_metric_card("📆", "DÍAS PROM. (ASIGNACIÓN)",
                f"{dias:.1f} días", color, COLORS['secondary'])
            st.metric("Citas en muestra", f"{int(esp.get('TotalCitas', 0)):,}")
            st.success("✅ Valor esperado ~8.7 días — validado contra SIHOS nativo (7.92 días).")

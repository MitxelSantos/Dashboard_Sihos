"""
Módulo Reportes — Sub-tabs: Interoperabilidad RDA + Otros reportes (placeholders)
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.db_connector import get_db_connector
from utils.queries import SIHOSQueries, dataframe_to_excel
from config.settings import COLORS
from components.widgets import render_section_banner, render_section_divider
from components.layout import render_footer


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _render_rda_interoperabilidad():
    """Sub-sección completa de Interoperabilidad RDA."""
    db = get_db_connector()
    queries = SIHOSQueries()

    # -----------------------------------------------------------------------
    # FILTROS
    # -----------------------------------------------------------------------
    col_fecha1, col_fecha2, col_estado, col_busqueda = st.columns(4)

    with col_fecha1:
        fecha_ini = st.date_input(
            "Fecha inicio",
            value=date.today().replace(day=1),
            key="rda_fecha_ini"
        )
    with col_fecha2:
        fecha_fin = st.date_input(
            "Fecha fin",
            value=date.today(),
            key="rda_fecha_fin"
        )
    with col_estado:
        estado_opciones = {
            "Todos": None,
            "🟢 Enviado": 56,
            "🟡 Pendiente": 57,
            "🔴 Rechazado": 58,
        }
        estado_sel = st.selectbox(
            "Estado", options=list(estado_opciones.keys()), key="rda_estado"
        )
        estado_id = estado_opciones[estado_sel]
    with col_busqueda:
        busqueda = st.text_input(
            "Buscar por admisión",
            placeholder="Ej: 202605270608",
            key="rda_busqueda"
        )

    render_section_divider()

    # -----------------------------------------------------------------------
    # KPIs DE RESUMEN (rango seleccionado)
    # -----------------------------------------------------------------------
    params_summary = {"fecha_inicio": str(fecha_ini), "fecha_fin": str(fecha_fin)}
    df_summary = db.execute_query(queries.get_rda_summary(), params_summary)

    if not df_summary.empty:
        row = df_summary.iloc[0]
        total = int(row.get("Total") or 0) or 1
        enviados   = int(row.get("Enviados",   0) or 0)
        pendientes = int(row.get("Pendientes", 0) or 0)
        rechazados = int(row.get("Rechazados", 0) or 0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Total RDA",    f"{total:,}")
        c2.metric("🟢 Enviados",    f"{enviados:,}",
                  delta=f"{enviados / total * 100:.1f}%")
        c3.metric("🟡 Pendientes",  f"{pendientes:,}",
                  delta=f"{pendientes / total * 100:.1f}%")
        c4.metric("🔴 Rechazados",  f"{rechazados:,}",
                  delta=f"{rechazados / total * 100:.1f}%",
                  delta_color="inverse")

    render_section_divider()

    # -----------------------------------------------------------------------
    # TABLA PRINCIPAL
    # -----------------------------------------------------------------------
    st.markdown("#### Tabla de envíos por admisión")

    params_tabla: dict = {
        "fecha_inicio": str(fecha_ini),
        "fecha_fin":    str(fecha_fin),
    }
    if estado_id is not None:
        params_tabla["estado_id"] = str(estado_id)
    if busqueda:
        params_tabla["busqueda"] = f"%{busqueda}%"

    with st.spinner("Cargando tabla RDA…"):
        df_rda = db.execute_query(
            queries.get_rda_tabla(estado_id=estado_id, busqueda=busqueda or None),
            params_tabla,
        )

    if df_rda.empty:
        st.info("No se encontraron registros para los filtros seleccionados.")
        return

    st.caption(f"{len(df_rda)} admisiones encontradas (máx. 500)")

    seleccion = st.dataframe(
        df_rda,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="rda_tabla_sel",
    )

    # -----------------------------------------------------------------------
    # PANEL DE DETALLE
    # -----------------------------------------------------------------------
    if seleccion.selection.rows:
        fila = df_rda.iloc[seleccion.selection.rows[0]]
        consadmi_sel = fila["Admision"]

        st.divider()
        st.subheader(f"Detalle — Admisión {consadmi_sel}")
        st.write(f"**Paciente:** {fila['Paciente']}")

        df_detalle = db.execute_query(
            queries.get_rda_detalle(),
            {"consadmi": str(consadmi_sel)},
        )

        if df_detalle.empty:
            st.info("Sin registros de detalle para esta admisión.")
        else:
            import json as _json

            for _, row in df_detalle.iterrows():
                tipo   = row.get("TipoRDA", "—")
                estado = row.get("Estado",  "—")

                # Parsear JSON en Python (sin depender de funciones MySQL)
                http_code = ""
                num_vida  = None
                msg_error = None
                raw_json  = row.get("JsonRespuesta")
                if raw_json and isinstance(raw_json, str):
                    try:
                        j = _json.loads(raw_json)
                        http_code = str(j.get("http_code", ""))
                        respuesta = j.get("respuesta", {})
                        if http_code == "200":
                            entries = respuesta.get("entry", [])
                            if entries:
                                num_vida = entries[0].get("resource", {}).get("id")
                        elif http_code == "400":
                            issues = respuesta.get("issue", [])
                            if issues:
                                codings = issues[0].get("details", {}).get("coding", [])
                                if codings:
                                    msg_error = codings[0].get("display")
                    except Exception:
                        pass

                with st.expander(f"{tipo} — {estado}", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Usuario SIHOS:** {row.get('UsuarioSIHOS', '—')}")
                        st.write(f"**Fecha envío:** {row.get('FechaEnvio', '—')}")
                        st.write(f"**HTTP:** {http_code or '—'}")
                    with col_b:
                        if http_code == "200" and num_vida:
                            st.success(f"**Número VIDA:** `{num_vida}`")
                        elif http_code == "400" and msg_error:
                            st.error(f"**Error:** {msg_error}")
                        else:
                            st.info("Pendiente de procesamiento")

                    if row.get("FechaRespuesta"):
                        st.caption(f"Respuesta Ministerio: {row['FechaRespuesta']}")


def _render_resolucion_373():
    """Sub-sección Resolución 373 — Tiempos de espera en urgencias."""
    import plotly.express as px
    import plotly.graph_objects as go

    db = get_db_connector()
    queries = SIHOSQueries()

    fecha_ini = st.session_state.get('sidebar_fecha_inicio',
                                     date.today().replace(day=1))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', date.today())

    st.info(
        "Indicadores de oportunidad de atención en urgencias según **Resolución 3678 de 2023** "
        "(antes Resolución 5596/2015). Tiempo medido desde el ingreso hasta la clasificación de triage.",
        icon="ℹ️"
    )

    params = {"fecha_inicio": str(fecha_ini), "fecha_fin": str(fecha_fin)}

    with st.spinner("Cargando indicadores 373..."):
        df_kpis   = db.execute_query(queries.get_373_kpis(), params)
        df_triage = db.execute_query(queries.get_373_por_triage(), params)
        df_causa  = db.execute_query(queries.get_373_por_causa(), params)
        df_serv   = db.execute_query(queries.get_373_por_servicio(), params)
        df_tend   = db.execute_query(queries.get_373_tendencia_diaria(), params)

    if df_kpis.empty or df_triage.empty:
        st.warning("No hay datos de urgencias para el período seleccionado.")
        return

    # -------------------------------------------------------------------
    # KPIs GENERALES
    # -------------------------------------------------------------------
    kpi = df_kpis.iloc[0]
    total    = int(kpi.get("TotalUrgencias", 0))
    prom_esp = float(kpi.get("PromEsperaMin", 0) or 0)
    dentro   = int(kpi.get("DentroStd", 0))
    fuera    = int(kpi.get("FueraStd", 0))
    pct_ok   = round(dentro / total * 100, 1) if total else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚨 Total urgencias",     f"{total:,}")
    col2.metric("⏱️ Espera promedio",     f"{prom_esp:.1f} min")
    col3.metric("✅ Dentro del estándar", f"{dentro:,}",
                delta=f"{pct_ok}%")
    col4.metric("❌ Fuera del estándar",  f"{fuera:,}",
                delta=f"{100-pct_ok:.1f}%", delta_color="inverse")

    render_section_divider()

    # -------------------------------------------------------------------
    # SEMÁFORO POR NIVEL DE TRIAGE
    # -------------------------------------------------------------------
    st.markdown("#### ⏱️ Tiempo de espera por nivel de triage vs estándar Res. 373")

    if not df_triage.empty:
        fig_triage = go.Figure()

        fig_triage.add_trace(go.Bar(
            name="Tiempo promedio (min)",
            x=df_triage["NivelTriage"],
            y=df_triage["PromEsperaMin"],
            marker_color=[
                COLORS['success'] if row["PromEsperaMin"] <= row["LimiteStdMin"]
                else COLORS['danger']
                for _, row in df_triage.iterrows()
            ],
            text=df_triage["PromEsperaMin"].apply(lambda x: f"{x:.1f} min"),
            textposition="outside"
        ))

        fig_triage.add_trace(go.Scatter(
            name="Límite estándar (min)",
            x=df_triage["NivelTriage"],
            y=df_triage["LimiteStdMin"],
            mode="lines+markers",
            line=dict(color=COLORS['warning'], width=2, dash="dash"),
            marker=dict(size=8)
        ))

        fig_triage.update_layout(
            height=400,
            xaxis_title="Nivel de Triage",
            yaxis_title="Minutos",
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_triage, use_container_width=True)

        st.markdown("##### Detalle por nivel")
        for _, row in df_triage.iterrows():
            prom    = row["PromEsperaMin"]
            limite  = row["LimiteStdMin"]
            nivel   = row["NivelTriage"]
            total_n = int(row["Total"])
            icono   = "🟢" if prom <= limite else "🔴"
            estado  = "Dentro del estándar" if prom <= limite else "⚠️ Fuera del estándar"
            st.markdown(
                f"{icono} **{nivel}** — {total_n:,} casos — "
                f"Prom: **{prom:.1f} min** (límite: {limite} min) — *{estado}*"
            )

    render_section_divider()

    # -------------------------------------------------------------------
    # DISTRIBUCIÓN POR CAUSA EXTERNA Y SERVICIO
    # -------------------------------------------------------------------
    col_c, col_s = st.columns(2)

    with col_c:
        if not df_causa.empty:
            fig_causa = px.bar(
                df_causa,
                x="PromEsperaMin", y="CausaExterna",
                orientation="h",
                color="PromEsperaMin",
                color_continuous_scale="Oranges",
                title="Espera promedio por Causa Externa",
                text="Total"
            )
            fig_causa.update_traces(texttemplate="%{text} casos",
                                    textposition="outside")
            fig_causa.update_layout(
                height=350,
                yaxis={"categoryorder": "total ascending"},
                showlegend=False
            )
            st.plotly_chart(fig_causa, use_container_width=True)

    with col_s:
        if not df_serv.empty:
            fig_serv = px.bar(
                df_serv,
                x="PromEsperaMin", y="Servicio",
                orientation="h",
                color="PromEsperaMin",
                color_continuous_scale="Blues",
                title="Espera promedio por Servicio",
                text="Total"
            )
            fig_serv.update_traces(texttemplate="%{text} casos",
                                   textposition="outside")
            fig_serv.update_layout(
                height=350,
                yaxis={"categoryorder": "total ascending"},
                showlegend=False
            )
            st.plotly_chart(fig_serv, use_container_width=True)

    render_section_divider()

    # -------------------------------------------------------------------
    # TENDENCIA DIARIA
    # -------------------------------------------------------------------
    if not df_tend.empty:
        st.markdown("#### 📈 Tendencia diaria de espera")
        fig_tend = go.Figure()
        fig_tend.add_trace(go.Scatter(
            x=df_tend["Fecha"],
            y=df_tend["PromEsperaMin"],
            mode="lines+markers",
            name="Espera promedio (min)",
            line=dict(color=COLORS['primary'], width=2),
            fill="tozeroy"
        ))
        fig_tend.add_hline(
            y=30, line_dash="dash", line_color=COLORS['warning'],
            annotation_text="Estándar Triage 2 (30 min)"
        )
        fig_tend.update_layout(
            height=350,
            xaxis_title="Fecha",
            yaxis_title="Minutos promedio",
            hovermode="x unified"
        )
        st.plotly_chart(fig_tend, use_container_width=True)

    # -------------------------------------------------------------------
    # TABLA DESCARGABLE
    # -------------------------------------------------------------------
    with st.expander("📋 Ver tabla completa por nivel de triage"):
        st.dataframe(df_triage, use_container_width=True, hide_index=True)
        csv = df_triage.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 Descargar CSV",
            data=csv,
            file_name=f"res373_triage_{fecha_ini}_{fecha_fin}.csv",
            mime="text/csv"
        )
        st.download_button(
            "📥 Descargar Excel",
            data=dataframe_to_excel(df_triage),
            file_name=f"res373_triage_{fecha_ini}_{fecha_fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def _render_auditoria_cierres(db, queries):
    """Auditoría de admisiones con cierre tardío."""
    import plotly.express as px

    st.markdown("### 🔍 Auditoría — Admisiones con Cierre Tardío")
    st.info(
        "Admisiones de hospitalización cuya **fecha de egreso coincide con la fecha de modificación**, "
        "con más de 30 días de diferencia respecto al ingreso. "
        "Esto indica admisiones que no fueron cerradas oportunamente en el sistema. "
        "**No representan pacientes realmente hospitalizados por ese período.**",
        icon="⚠️"
    )

    fecha_ini = st.session_state.get('sidebar_fecha_inicio', date.today().replace(day=1))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', date.today())
    params = {"fecha_inicio": str(fecha_ini), "fecha_fin": str(fecha_fin)}

    df_audit = db.execute_query(queries.get_cierres_tardios(), params)

    if not df_audit.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total casos", f"{len(df_audit):,}")
        col2.metric("Usuarios involucrados", f"{df_audit['UsuarioCierre'].nunique():,}")
        col3.metric("Días máx. de diferencia", f"{int(df_audit['DiasEstancia'].max()):,}")

        dist_usuario = (
            df_audit.groupby('UsuarioCierre')
            .agg(Total=('ConsAdmi', 'count'), DiasPromedio=('DiasEstancia', 'mean'))
            .reset_index()
            .sort_values('Total', ascending=False)
        )
        dist_usuario['DiasPromedio'] = dist_usuario['DiasPromedio'].round(0)

        fig = px.bar(
            dist_usuario,
            x='Total', y='UsuarioCierre',
            orientation='h',
            color='DiasPromedio',
            color_continuous_scale='Reds',
            title='Cierres tardíos por usuario (color = promedio de días)',
            text='Total'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            height=max(300, len(dist_usuario) * 40),
            yaxis={'categoryorder': 'total ascending'},
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_audit, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Descargar para auditoría CSV",
            df_audit.to_csv(index=False, encoding='utf-8-sig'),
            f"auditoria_cierres_tardios_{fecha_ini}_{fecha_fin}.csv",
            mime="text/csv"
        )
    else:
        st.success("✅ No se encontraron cierres tardíos en el período seleccionado.")


def _render_admisiones_sin_cerrar(db, queries):
    """Tab Admisiones sin Cerrar."""
    import plotly.express as px
    import io

    st.subheader("📂 Admisiones sin Cerrar")
    st.caption(
        "Admisiones con Cerrado=2, Anulado=2 y FechEgre IS NULL — "
        "el sistema las considera activas pero muchas corresponden a "
        "atenciones finalizadas no cerradas formalmente."
    )
    st.warning(
        "⚠️ **Total estimado: ~21,554 admisiones sin cerrar** (dato de auditoría mayo 2026). "
        "Solo 605 son de hoy o ayer — el 87% llevan más de 30 días. "
        "Las ambulatorias (TipoAten=1,4) no bloquean camas pero afectan RIPS y estadísticas."
    )

    with st.spinner("Cargando distribución..."):
        try:
            df_rango = db.execute_query(queries.get_admisiones_sin_cerrar_resumen(), {})
            asc_ok = True
        except Exception as e:
            st.error(f"Error: {e}")
            asc_ok = False

    if asc_ok and not df_rango.empty:
        total_asc   = int(df_rango['total'].sum())
        legitimas   = int(df_rango[df_rango['rango'].isin(['0. Hoy', '1. 1-2 días'])]['total'].sum())
        sospechosas = total_asc - legitimas

        k1, k2, k3 = st.columns(3)
        k1.metric("Total sin cerrar",      f"{total_asc:,}")
        k2.metric("Posiblemente activas",  f"{legitimas:,}",
                  delta="≤2 días", delta_color="normal")
        k3.metric("Probables errores",     f"{sospechosas:,}",
                  delta=">2 días", delta_color="inverse")

        st.divider()

        st.markdown("#### Distribución por antigüedad")
        colores = {
            '0. Hoy':           '#4CAF50',
            '1. 1-2 días':      '#8BC34A',
            '2. 3-7 días':      '#FFC107',
            '3. 8-30 días':     '#FF9800',
            '4. 31-90 días':    '#F44336',
            '5. 91-365 días':   '#B71C1C',
            '6. Más de 1 año':  '#4A148C',
        }
        fig_asc = px.bar(
            df_rango, x='rango', y='total',
            color='rango',
            color_discrete_map=colores,
            text='total',
            labels={'rango': 'Antigüedad', 'total': 'Admisiones'},
            height=350,
        )
        fig_asc.update_layout(showlegend=False, xaxis_title='', yaxis_title='Admisiones')
        fig_asc.update_traces(textposition='outside')
        st.plotly_chart(fig_asc, use_container_width=True)

        st.divider()

        st.markdown("#### Detalle — admisiones problemáticas")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            dias_min = st.slider("Días mínimos abierta", 0, 365, 30, step=1, key="asc_dias")
        with col_f2:
            tipo_opts = {
                'Todos': None,
                'Consulta Externa (1)': 1,
                'Hospitalización (2)': 2,
                'Urgencias (3)': 3,
                'PyP (4)': 4,
            }
            tipo_sel = st.selectbox("Tipo de atención", list(tipo_opts.keys()), key="asc_tipo")

        with st.spinner("Cargando detalle..."):
            try:
                df_det = db.execute_query(
                    queries.get_admisiones_sin_cerrar_detalle(
                        dias_minimo=dias_min,
                        tipo_aten=tipo_opts[tipo_sel]
                    ), {}
                )
            except Exception as e:
                df_det = pd.DataFrame()
                st.error(f"Error cargando detalle: {e}")

        if not df_det.empty:
            st.caption(f"Mostrando {len(df_det):,} admisiones (máx 500) con ≥{dias_min} días")
            st.dataframe(df_det, use_container_width=True, hide_index=True)

            buf = io.BytesIO()
            df_det.to_excel(buf, index=False, engine='openpyxl')
            buf.seek(0)
            st.download_button(
                "⬇️ Descargar Excel",
                data=buf,
                file_name=f"admisiones_sin_cerrar_{dias_min}d.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


def _render_camas_bloqueadas(db, queries):
    """Tab Camas Bloqueadas."""
    import plotly.express as px
    import io

    st.subheader("🛏️ Camas Bloqueadas")
    st.caption("Camas en CodiCama apuntando a admisiones que ya deberían estar liberadas.")
    st.info(
        "**Dos tipos de bloqueo:**\n\n"
        "🔴 **Bug Sinergia**: admisión CERRADA o ANULADA pero `CodiCama.ConsAdmi` "
        "no se limpió. Requiere intervención de Sinergia.\n\n"
        "🟠 **Proceso incompleto**: `FechEgre` registrada pero nadie ejecutó "
        "'Cerrar Historia'. Cama físicamente vacía. Responsable: personal del servicio."
    )

    with st.spinner("Cargando datos de camas..."):
        try:
            df_bug  = db.execute_query(queries.get_camas_bug_sinergia(), {})
            df_proc = db.execute_query(queries.get_camas_proceso_incompleto(), {})
            df_serv = db.execute_query(queries.get_camas_resumen_por_servicio(), {})
            camas_ok = True
        except Exception as e:
            st.error(f"Error: {e}")
            camas_ok = False

    if camas_ok:
        k1, k2, k3 = st.columns(3)
        k1.metric("🔴 Bug Sinergia",      len(df_bug),
                  delta="Requiere parche técnico", delta_color="inverse")
        k2.metric("🟠 Proceso incompleto", len(df_proc),
                  delta="Personal debe cerrar", delta_color="inverse")
        k3.metric("Total bloqueadas",      len(df_bug) + len(df_proc))

        st.divider()

        st.markdown("#### Bloqueos por servicio")
        if not df_serv.empty:
            fig_serv = px.bar(
                df_serv.head(15),
                x='CodiServ', y='total_bloqueadas',
                color_discrete_sequence=['#E53935'],
                text='total_bloqueadas',
                labels={'CodiServ': 'Servicio', 'total_bloqueadas': 'Camas bloqueadas'},
                height=320,
            )
            fig_serv.update_layout(xaxis_title='Código servicio', showlegend=False)
            fig_serv.update_traces(textposition='outside')
            st.plotly_chart(fig_serv, use_container_width=True)

        st.divider()

        sub_bug, sub_proc = st.tabs(["🔴 Bug Sinergia", "🟠 Proceso Incompleto"])

        with sub_bug:
            st.markdown(f"**{len(df_bug)} camas** con admisión CERRADA/ANULADA sin liberar")
            if not df_bug.empty:
                st.dataframe(df_bug, use_container_width=True, hide_index=True)
                buf = io.BytesIO()
                df_bug.to_excel(buf, index=False, engine='openpyxl')
                buf.seek(0)
                st.download_button(
                    "⬇️ Exportar Bug Sinergia", data=buf,
                    file_name="camas_bug_sinergia.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        with sub_proc:
            st.markdown(f"**{len(df_proc)} camas** con egreso registrado pero historia sin cerrar")
            if not df_proc.empty:
                def color_egreso(dias):
                    if dias <= 7:  return "🟡"
                    if dias <= 30: return "🟠"
                    return "🔴"
                df_proc = df_proc.copy()
                df_proc['alerta'] = df_proc['dias_desde_egreso'].apply(color_egreso)
                st.dataframe(df_proc, use_container_width=True, hide_index=True)
                buf2 = io.BytesIO()
                df_proc.to_excel(buf2, index=False, engine='openpyxl')
                buf2.seek(0)
                st.download_button(
                    "⬇️ Exportar Proceso Incompleto", data=buf2,
                    file_name="camas_proceso_incompleto.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


def _render_usuarios_sihos(db, queries):
    """Tab Usuarios SIHOS."""
    import plotly.express as px
    import io

    st.subheader("👥 Usuarios SIHOS")
    st.caption("Gestión de usuarios del sistema — firma digital, grupos de permisos, estado.")

    with st.spinner("Cargando usuarios..."):
        try:
            df_usr = db.execute_query(queries.get_usuarios_resumen(), {})
            df_grp = db.execute_query(queries.get_usuarios_por_grupo(), {})
            usr_ok = True
        except Exception as e:
            st.error(f"Error: {e}")
            usr_ok = False

    if usr_ok:
        df_uniq      = df_usr.drop_duplicates('Login')
        total_usr    = len(df_uniq)
        activos      = df_uniq['estado'].eq('Activo').sum()
        sin_firma    = df_uniq['tiene_firma'].eq('No').sum()
        sin_registro = df_uniq['registro_prof'].isna().sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total usuarios",        f"{total_usr:,}")
        k2.metric("Activos",               f"{activos:,}")
        k3.metric("Sin firma digital",     f"{sin_firma:,}",
                  delta=f"{sin_firma/total_usr*100:.0f}%" if total_usr else "0%",
                  delta_color="inverse")
        k4.metric("Sin reg. profesional",  f"{sin_registro:,}",
                  delta=f"{sin_registro/total_usr*100:.0f}%" if total_usr else "0%",
                  delta_color="inverse")

        st.divider()

        col_u1, col_u2 = st.columns([2, 1])

        with col_u1:
            st.markdown("#### Top grupos de permisos")
            fig_grp = px.bar(
                df_grp.head(20),
                x='total_usuarios', y='NombGrup',
                orientation='h',
                color='activos',
                color_continuous_scale='Blues',
                text='total_usuarios',
                labels={'total_usuarios': 'Usuarios', 'NombGrup': ''},
                height=520,
            )
            fig_grp.update_layout(
                yaxis=dict(autorange='reversed'),
                coloraxis_colorbar=dict(title='Activos'),
            )
            fig_grp.update_traces(textposition='outside')
            st.plotly_chart(fig_grp, use_container_width=True)

        with col_u2:
            st.markdown("#### Estado general")
            est_cnt = df_uniq['estado'].value_counts().reset_index()
            est_cnt.columns = ['Estado', 'Cantidad']
            fig_est = px.pie(
                est_cnt, names='Estado', values='Cantidad', hole=0.45,
                color='Estado',
                color_discrete_map={'Activo': '#4CAF50', 'Inactivo': '#9E9E9E'},
            )
            fig_est.update_traces(textinfo='percent+label')
            fig_est.update_layout(showlegend=False, height=250,
                                   margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_est, use_container_width=True)

            st.markdown("#### Firma digital")
            firma_cnt = df_uniq['tiene_firma'].value_counts().reset_index()
            firma_cnt.columns = ['Firma', 'Cantidad']
            fig_firma = px.pie(
                firma_cnt, names='Firma', values='Cantidad', hole=0.45,
                color='Firma',
                color_discrete_map={'Sí': '#2196F3', 'No': '#FF5722'},
            )
            fig_firma.update_traces(textinfo='percent+label')
            fig_firma.update_layout(showlegend=False, height=250,
                                     margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_firma, use_container_width=True)

        st.divider()

        st.markdown("#### Directorio de usuarios")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            estado_f = st.selectbox("Estado", ['Todos', 'Activo', 'Inactivo'], key="usr_estado")
        with col_f2:
            firma_f = st.selectbox("Firma digital", ['Todos', 'Sí', 'No'], key="usr_firma")
        with col_f3:
            grupos_disp = ['Todos'] + sorted(df_grp['NombGrup'].dropna().unique().tolist())
            grupo_f = st.selectbox("Grupo", grupos_disp, key="usr_grupo")

        df_filt = df_usr.copy()
        if estado_f != 'Todos':
            df_filt = df_filt[df_filt['estado'] == estado_f]
        if firma_f != 'Todos':
            df_filt = df_filt[df_filt['tiene_firma'] == firma_f]
        if grupo_f != 'Todos':
            df_filt = df_filt[df_filt['grupo_principal'] == grupo_f]

        cols_tabla = ['Login', 'Nombre', 'estado', 'tipo_personal',
                      'grupo_principal', 'tiene_firma', 'registro_prof', 'email']
        st.caption(f"Mostrando {len(df_filt):,} registros")
        st.dataframe(
            df_filt[cols_tabla].rename(columns={
                'Login': 'Login', 'Nombre': 'Nombre', 'estado': 'Estado',
                'tipo_personal': 'Tipo', 'grupo_principal': 'Grupo',
                'tiene_firma': 'Firma', 'registro_prof': 'Reg. Prof.', 'email': 'Email',
            }),
            use_container_width=True, hide_index=True
        )

        buf = io.BytesIO()
        df_filt[cols_tabla].to_excel(buf, index=False, engine='openpyxl')
        buf.seek(0)
        st.download_button(
            "⬇️ Exportar usuarios Excel", data=buf,
            file_name="usuarios_sihos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.divider()
        st.markdown("#### ⚠️ Alertas de seguridad")
        grupos_criticos = [1, 11, 199, 194]
        df_criticos = df_usr[
            df_usr['CodiGrup'].isin(grupos_criticos) & (df_usr['estado'] == 'Activo')
        ][['Login', 'Nombre', 'grupo_principal']].drop_duplicates()
        if not df_criticos.empty:
            st.warning(
                f"**{len(df_criticos)} usuarios activos** tienen permisos críticos "
                "(Administrador, Anular Facturas, Abrir-Cerrar Historias):"
            )
            st.dataframe(df_criticos, use_container_width=True, hide_index=True)


def _render_sismed(db, queries):
    """Tab SISMED — Servicios y Procedimientos Facturados."""
    import calendar
    import io
    import plotly.express as px
    import plotly.graph_objects as go

    st.subheader("📦 SISMED — Servicios y Procedimientos Facturados")
    st.caption(
        "Fuente: DetaFact (CodiDocu='LIQ') · "
        "Nombre: CodiProc.NombProc · "
        "Clave: DetaFact.CodiServ = CodiProc.CodiProc · "
        "Fecha: FechDigi"
    )

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sismed_ini = st.date_input(
            "Desde", value=date(date.today().year, 1, 1), key="sismed_ini"
        )
    with col_f2:
        sismed_fin = st.date_input(
            "Hasta", value=date.today(), key="sismed_fin"
        )

    params_sismed = {"fecha_inicio": str(sismed_ini), "fecha_fin": str(sismed_fin)}

    with st.spinner("Cargando datos SISMED..."):
        try:
            df_kpis = db.execute_query(queries.get_sismed_kpis(), params_sismed)
            df_top  = db.execute_query(queries.get_sismed_top_items(top_n=20), params_sismed)
            df_tend = db.execute_query(queries.get_sismed_tendencia(), params_sismed)
            df_pos  = db.execute_query(queries.get_sismed_pos_distribucion(), params_sismed)
            sismed_ok = True
        except Exception as e:
            st.error(f"Error cargando SISMED: {e}")
            sismed_ok = False

    if sismed_ok:
        st.markdown("#### Resumen del período")
        if not df_kpis.empty:
            kpis = df_kpis.iloc[0]
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Servicios distintos", f"{int(kpis.get('items_distintos', 0) or 0):,}")
            k2.metric("Unidades facturadas",  f"{int(kpis.get('total_unidades', 0) or 0):,}")
            k3.metric("Valor total",          f"${float(kpis.get('valor_total', 0) or 0) / 1e9:.2f}B")
            k4.metric("Precio promedio",      f"${float(kpis.get('precio_promedio', 0) or 0):,.0f}")

        st.divider()

        st.markdown("#### Tendencia mensual de ventas")
        if not df_tend.empty:
            hoy        = date.today()
            mes_actual = hoy.strftime("%Y-%m")
            dias_mes   = calendar.monthrange(hoy.year, hoy.month)[1]
            if hoy.day / dias_mes < 0.5:
                df_tend_graf = df_tend[df_tend["mes"] < mes_actual].copy()
                st.caption(f"⚠️ Mes en curso ({mes_actual}) excluido por estar incompleto.")
            else:
                df_tend_graf = df_tend.copy()

            fig_tend = go.Figure()
            fig_tend.add_trace(go.Bar(
                x=df_tend_graf["mes"], y=df_tend_graf["total_valor"] / 1e9,
                name="Valor ($B)", marker_color="#1f77b4", yaxis="y1",
            ))
            fig_tend.add_trace(go.Scatter(
                x=df_tend_graf["mes"], y=df_tend_graf["total_unidades"],
                name="Unidades", mode="lines+markers",
                marker_color="#ff7f0e", yaxis="y2",
            ))
            fig_tend.update_layout(
                xaxis_title="Mes",
                yaxis=dict(title="Valor ($B COP)", tickformat=".1f"),
                yaxis2=dict(title="Unidades", overlaying="y", side="right"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                height=380,
            )
            st.plotly_chart(fig_tend, use_container_width=True)
        else:
            st.info("Sin datos de tendencia para el período seleccionado.")

        st.divider()

        col_top, col_pos = st.columns([3, 1])

        with col_top:
            st.markdown("#### Top 20 servicios por valor facturado")
            if not df_top.empty:
                df_top_disp = df_top.copy()
                df_top_disp["es_pos_txt"]    = df_top_disp["es_pos"].map({1: "✅ POS", 0: "❌ No POS"})
                df_top_disp["total_valor_M"] = (df_top_disp["total_valor"] / 1e6).round(1)
                df_top_disp["precio_fmt"]    = df_top_disp["precio_promedio"].apply(lambda x: f"${x:,.0f}")
                df_top_disp["desc_corta"]    = df_top_disp["descripcion"].str[:60]

                fig_top = px.bar(
                    df_top_disp.head(15),
                    x="total_valor_M", y="desc_corta",
                    orientation="h",
                    color="es_pos_txt",
                    color_discrete_map={"✅ POS": "#2196F3", "❌ No POS": "#FF5722"},
                    labels={"total_valor_M": "Valor ($M COP)", "desc_corta": ""},
                    height=520,
                )
                fig_top.update_layout(legend_title="Tipo", yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_top, use_container_width=True)

                with st.expander("Ver tabla completa Top 20"):
                    st.dataframe(
                        df_top_disp[[
                            "codigo", "descripcion", "categoria",
                            "total_unidades", "total_valor_M", "precio_fmt", "es_pos_txt"
                        ]].rename(columns={
                            "codigo": "Código", "descripcion": "Descripción",
                            "categoria": "Categoría", "total_unidades": "Unidades",
                            "total_valor_M": "Valor ($M)", "precio_fmt": "Precio Prom.",
                            "es_pos_txt": "POS",
                        }),
                        use_container_width=True, hide_index=True,
                    )
            else:
                st.info("Sin datos de servicios para el período.")

        with col_pos:
            st.markdown("#### POS vs No POS")
            if not df_pos.empty:
                df_pos_disp = df_pos.copy()
                df_pos_disp["tipo"] = df_pos_disp["EsPOS"].map({1: "POS", 0: "No POS"})
                fig_pos = px.pie(
                    df_pos_disp, names="tipo", values="valor_total",
                    color="tipo",
                    color_discrete_map={"POS": "#2196F3", "No POS": "#FF5722"},
                    hole=0.45,
                )
                fig_pos.update_traces(textinfo="percent+label")
                fig_pos.update_layout(showlegend=False, height=280, margin=dict(t=10, b=10))
                st.plotly_chart(fig_pos, use_container_width=True)

                for _, row in df_pos_disp.iterrows():
                    st.caption(
                        f"**{row['tipo']}**: {row['items_distintos']} servicios · "
                        f"{int(row['unidades'] or 0):,} und · "
                        f"${row['valor_total'] / 1e6:.1f}M"
                    )
            else:
                st.info("Sin datos POS/No POS.")

        st.divider()

        st.markdown("#### Exportar datos SISMED")
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_top.to_excel(writer,  sheet_name="Top_Servicios", index=False)
            df_tend.to_excel(writer, sheet_name="Tendencia",     index=False)
            df_pos.to_excel(writer,  sheet_name="POS_NoPOS",     index=False)
        buf.seek(0)
        st.download_button(
            label="⬇️ Descargar Excel SISMED",
            data=buf,
            file_name=f"SISMED_{sismed_ini}_{sismed_fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ---------------------------------------------------------------------------
# Punto de entrada del módulo
# ---------------------------------------------------------------------------

def render_reportes():
    """Función principal del módulo Reportes."""
    render_section_banner("📊", "Reportes")

    db = get_db_connector()
    queries = SIHOSQueries()

    (tab_rda, tab_373, tab_cierres, tab_sin_cerrar,
     tab_camas, tab_usuarios, tab_rips, tab_373exp, tab_sismed) = st.tabs([
        "🔗 Interoperabilidad RDA",
        "🚨 Resolución 373",
        "🔍 Auditoría Cierres",
        "📂 Admisiones sin Cerrar",
        "🛏️ Camas Bloqueadas",
        "👥 Usuarios SIHOS",
        "📄 RIPS",
        "📋 Res. 373 (export)",
        "🚀 SISMED",
    ])

    with tab_rda:
        _render_rda_interoperabilidad()

    with tab_373:
        _render_resolucion_373()

    with tab_cierres:
        _render_auditoria_cierres(db, queries)

    with tab_sin_cerrar:
        _render_admisiones_sin_cerrar(db, queries)

    with tab_camas:
        _render_camas_bloqueadas(db, queries)

    with tab_usuarios:
        _render_usuarios_sihos(db, queries)

    with tab_rips:
        st.info("📄 **RIPS** — Próximamente disponible")

    with tab_373exp:
        st.info("📋 **Resolución 373 (exportación)** — Próximamente disponible")

    with tab_sismed:
        _render_sismed(db, queries)

    render_footer()

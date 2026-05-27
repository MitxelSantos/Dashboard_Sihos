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
from utils.queries import SIHOSQueries
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


def _render_otros_reportes():
    """Sub-sección de reportes futuros (placeholders)."""
    st.divider()
    st.subheader("Otros reportes")
    st.caption("Las siguientes secciones estarán disponibles en próximas versiones.")

    col1, col2, col3 = st.columns(3)
    for col, nombre, icono in zip(
        [col1, col2, col3],
        ["RIPS", "SISMED", "IPS Primaria"],
        ["📄", "💊", "🏥"],
    ):
        with col:
            st.info(f"{icono} **{nombre}**\n\n_Próximamente disponible_")


# ---------------------------------------------------------------------------
# Punto de entrada del módulo
# ---------------------------------------------------------------------------

def render_reportes():
    """Función principal del módulo Reportes."""
    render_section_banner("📊", "Reportes")

    tab_rda, tab_373, tab_otros = st.tabs([
        "🔗 Interoperabilidad RDA",
        "🚨 Resolución 373 — Urgencias",
        "📋 Otros reportes"
    ])

    with tab_rda:
        _render_rda_interoperabilidad()

    with tab_373:
        _render_resolucion_373()

    with tab_otros:
        _render_otros_reportes()

    render_footer()

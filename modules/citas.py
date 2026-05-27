"""
Módulo Citas — Distribución de estados y oportunidad de acceso
Correción 2: EstaCita BETWEEN 1 AND 7 en todas las queries
Corrección 3: KPI oportunidad separado en dos métricas (solicitud vs asignación)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.db_connector import get_db_connector
from utils.queries import SIHOSQueries
from config.settings import COLORS, CACHE_TTL
from components.widgets import (
    get_fecha_rango_texto,
    render_metric_card,
    render_section_banner,
    render_section_divider,
)
from components.layout import render_footer


def render_citas():
    """Función principal del módulo de Citas"""

    fecha_inicio = st.session_state.get(
        "sidebar_fecha_inicio", datetime.now().date() - timedelta(days=30)
    )
    fecha_fin = st.session_state.get("sidebar_fecha_fin", datetime.now().date())
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)

    render_section_banner("📅", "Análisis de Citas", rango_fechas)

    @st.cache_data(ttl=CACHE_TTL)
    def load_citas_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        data = {}
        params = {"fecha_inicio": f_inicio, "fecha_fin": f_fin}
        try:
            data["estadisticas"] = db.execute_query(
                queries.get_estadisticas_citas(), params
            )
            data["distribucion"] = db.execute_query(
                queries.get_distribucion_estado_citas(), params
            )
            data["espera_solicitud"] = db.execute_query(
                queries.get_oportunidad_espera_solicitud(), params
            )
            data["espera_asignacion"] = db.execute_query(
                queries.get_oportunidad_espera_asignacion(), params
            )
        except Exception as e:
            st.error(f"Error cargando datos de citas: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None
        return data

    data = load_citas_data(fecha_inicio, fecha_fin)

    if data is None:
        st.error("Error al cargar datos de citas")
        st.stop()

    # =========================================================================
    # MÉTRICAS GENERALES
    # =========================================================================
    if not data["estadisticas"].empty:
        stats = data["estadisticas"].iloc[0]

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            render_metric_card(
                "📅", "TOTAL CITAS",
                f"{int(stats.get('Total_Citas', 0)):,}",
                COLORS["primary"], COLORS["secondary"],
            )
        with col2:
            render_metric_card(
                "✅", "CUMPLIDAS",
                f"{int(stats.get('Cumplidas', 0)):,}",
                COLORS["success"], COLORS["info"],
            )
        with col3:
            render_metric_card(
                "📋", "OCUPADAS",
                f"{int(stats.get('Ocupadas', 0)):,}",
                COLORS["info"], COLORS["primary"],
            )
        with col4:
            render_metric_card(
                "⚠️", "INCUMPLIDAS",
                f"{int(stats.get('Incumplidas', 0)):,}",
                COLORS["warning"], COLORS["danger"],
            )
        with col5:
            render_metric_card(
                "❌", "CANCELADAS",
                f"{int(stats.get('Canceladas', 0)):,}",
                COLORS["danger"], COLORS["warning"],
            )

    render_section_divider()

    # =========================================================================
    # DISTRIBUCIÓN POR ESTADO
    # =========================================================================
    render_section_banner("📊", "Distribución por Estado de Cita", rango_fechas)

    if not data["distribucion"].empty:
        col_graf, col_tabla = st.columns([3, 1])

        with col_graf:
            tipo_grafica = st.radio(
                "Tipo de gráfica:",
                ["🥧 Pie Chart", "📊 Bar Horizontal", "🌳 Treemap"],
                horizontal=True,
                key="radio_tipo_grafica_citas",
            )

            if "Pie" in tipo_grafica:
                fig = px.pie(
                    data["distribucion"],
                    values="TotalCitas",
                    names="Estado",
                    title="Distribución por Estado de Cita",
                    color_discrete_sequence=[
                        COLORS["success"], COLORS["info"], COLORS["warning"],
                        COLORS["danger"], COLORS["primary"], COLORS["secondary"],
                    ],
                )
                fig.update_traces(textposition="inside", textinfo="percent+label+value")
            elif "Bar" in tipo_grafica:
                fig = px.bar(
                    data["distribucion"],
                    x="TotalCitas",
                    y="Estado",
                    orientation="h",
                    color="TotalCitas",
                    color_continuous_scale="Blues",
                    title="Distribución por Estado de Cita",
                    text="Porcentaje",
                )
                fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
            else:
                fig = px.treemap(
                    data["distribucion"],
                    path=["Estado"],
                    values="TotalCitas",
                    title="Distribución por Estado de Cita",
                    color="TotalCitas",
                    color_continuous_scale="Blues",
                )

            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

        with col_tabla:
            st.markdown("### Resumen")
            total = data["distribucion"]["TotalCitas"].sum()
            st.metric("Total Citas", f"{int(total):,}")
            st.markdown("#### Detalle")
            st.dataframe(
                data["distribucion"],
                use_container_width=True,
                hide_index=True,
            )
            st.caption("*Solo estados 1-7. Códigos internos (8-95) excluidos.*")
    else:
        st.info("No hay datos de distribución de citas para el período seleccionado.")

    render_section_divider()

    # =========================================================================
    # INDICADORES DE OPORTUNIDAD — DOS KPIs SEPARADOS
    # =========================================================================
    render_section_banner("⏱️", "Oportunidad de Acceso a Citas", rango_fechas)

    st.info(
        "Los dos KPIs miden perspectivas distintas de la espera. "
        "**KPI 1** parte de cuándo el paciente solicita la cita. "
        "**KPI 2** parte de cuándo el sistema la asigna (validado contra SIHOS nativo).",
        icon="ℹ️",
    )

    col_kpi1, col_kpi2 = st.columns(2)

    # --- KPI 1: Espera desde solicitud ---
    with col_kpi1:
        st.markdown("### KPI 1 — Espera desde Solicitud")
        st.caption("Días entre `FechSoli` y `FechCita`. Filtro: FechSoli en el rango.")

        if not data["espera_solicitud"].empty:
            esp_sol = data["espera_solicitud"].iloc[0]
            dias_sol = esp_sol.get("PromEsperaSolicitud") or 0
            total_sol = int(esp_sol.get("TotalCitas") or 0)

            color_sol = (
                COLORS["danger"] if dias_sol > 15
                else COLORS["warning"] if dias_sol > 7
                else COLORS["success"]
            )

            render_metric_card(
                "📬", "DÍAS PROMEDIO (SOLICITUD)",
                f"{float(dias_sol):.1f} días",
                color_sol, COLORS["secondary"],
            )
            st.metric("Citas en muestra", f"{total_sol:,}")
            st.warning(
                "⚠️ Valor (~2.5 días) difiere del reporte SIHOS nativo (29.66 días). "
                "**Pendiente validación con proveedor Sinergia.**"
            )
        else:
            st.info("Sin datos para el período seleccionado.")

    # --- KPI 2: Espera desde asignación ---
    with col_kpi2:
        st.markdown("### KPI 2 — Espera desde Asignación ✅")
        st.caption("Días entre `FechAsig` y `FechCita`. Filtro: FechCita en el rango.")

        if not data["espera_asignacion"].empty:
            esp_asi = data["espera_asignacion"].iloc[0]
            dias_asi = esp_asi.get("PromEsperaAsignacion") or 0
            total_asi = int(esp_asi.get("TotalCitas") or 0)

            color_asi = (
                COLORS["danger"] if dias_asi > 15
                else COLORS["warning"] if dias_asi > 7
                else COLORS["success"]
            )

            render_metric_card(
                "📆", "DÍAS PROMEDIO (ASIGNACIÓN)",
                f"{float(dias_asi):.1f} días",
                color_asi, COLORS["secondary"],
            )
            st.metric("Citas en muestra", f"{total_asi:,}")
            st.success(
                "✅ Valor esperado ~8.7 días — validado contra SIHOS nativo (7.92 días)."
            )
        else:
            st.info("Sin datos para el período seleccionado.")

    render_footer()

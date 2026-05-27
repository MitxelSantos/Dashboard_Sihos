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
            for _, row in df_detalle.iterrows():
                tipo  = row.get("TipoRDA", "—")
                estado = row.get("Estado",  "—")
                with st.expander(f"{tipo} — {estado}", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Usuario SIHOS:** {row.get('UsuarioSIHOS', '—')}")
                        st.write(f"**Fecha envío:** {row.get('FechaEnvio', '—')}")
                        st.write(f"**HTTP:** {row.get('HttpCode', '—')}")
                    with col_b:
                        http = str(row.get("HttpCode") or "")
                        num_vida = row.get("NumeroVIDA")
                        msg_error = row.get("MensajeError")

                        if http == "200" and num_vida:
                            st.success(f"**Número VIDA:** `{num_vida}`")
                        elif http == "400" and msg_error:
                            st.error(f"**Error:** {msg_error}")
                        else:
                            st.info("Pendiente de procesamiento")

                    if row.get("FechaRespuesta"):
                        st.caption(f"Respuesta Ministerio: {row['FechaRespuesta']}")


def _render_otros_reportes():
    """Sub-sección de reportes futuros (placeholders)."""
    st.divider()
    st.subheader("Otros reportes")
    st.caption("Las siguientes secciones estarán disponibles en próximas versiones.")

    col1, col2, col3 = st.columns(3)
    for col, nombre, icono in zip(
        [col1, col2, col3],
        ["RIPS", "Resolución 373", "SISMED"],
        ["📄", "📋", "💊"],
    ):
        with col:
            st.info(f"{icono} **{nombre}**\n\n_Próximamente disponible_")


# ---------------------------------------------------------------------------
# Punto de entrada del módulo
# ---------------------------------------------------------------------------

def render_reportes():
    """Función principal del módulo Reportes."""
    render_section_banner("📊", "Reportes")

    tab_rda, tab_otros = st.tabs(["🔗 Interoperabilidad RDA", "📋 Otros reportes"])

    with tab_rda:
        _render_rda_interoperabilidad()

    with tab_otros:
        _render_otros_reportes()

    render_footer()

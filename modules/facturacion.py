"""
Módulo Facturación - Análisis Completo

Arquitectura (sep-2026): una sola query a nivel de factura
(SIHOSQueries.get_facturacion_detalle_periodo) alimenta TODO el tab — KPIs,
distribución, top facturas y por facturador — calculado con pandas sobre ese
mismo DataFrame. Antes cada sección tenía su propia query SQL y algunas sumaban
EncaFact.ValoTota (a veces $0 si la liquidación no estaba "causada") mientras
otras sumaban DetaFact (siempre real) — eso hacía que las tarjetas KPI y las
gráficas de abajo no cuadraran entre sí. Ver docstring de la query para el
detalle del bug y su impacto medido.
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
from utils.queries import SIHOSQueries, dataframe_to_excel
from config.settings import COLORS, CACHE_TTL
from components.widgets import (
    get_fecha_rango_texto,
    render_metric_card,
    render_section_banner,
    render_heading_help,
    render_section_divider
)
from components.layout import render_footer

PALETA = [
    COLORS['primary'], COLORS['info'], COLORS['success'],
    COLORS['warning'], COLORS['secondary'], COLORS['danger'],
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#96CEB4'
]

RANGOS_VALOR = [
    (0, 100_000, 'Menos de $100K'),
    (100_000, 500_000, '$100K - $500K'),
    (500_000, 1_000_000, '$500K - $1M'),
    (1_000_000, 5_000_000, '$1M - $5M'),
    (5_000_000, 10_000_000, '$5M - $10M'),
    (10_000_000, float('inf'), 'Más de $10M'),
]


def _asignar_rango(valor):
    for piso, techo, etiqueta in RANGOS_VALOR:
        if piso <= valor < techo:
            return etiqueta
    return RANGOS_VALOR[-1][2]


def _extraer_click(evento, campo_nombre):
    """Extrae las categorías seleccionadas de un st.plotly_chart(on_select='rerun').
    Requiere que la figura se haya creado con custom_data=[campo_nombre].
    Soporta multiselección (Shift+clic, o arrastrar un recuadro): retorna una lista de
    categorías únicas, o None si no hay selección activa."""
    if not evento:
        return None
    puntos = evento.get('selection', {}).get('points', [])
    categorias = []
    for punto in puntos:
        customdata = punto.get('customdata')
        if customdata and customdata[0] not in categorias:
            categorias.append(customdata[0])
    return categorias or None


def _etiqueta_seleccion(categorias):
    """Texto corto para títulos/archivos: 'A' o 'A, B, C (+2 más)'."""
    if len(categorias) <= 3:
        return ", ".join(str(c) for c in categorias)
    return ", ".join(str(c) for c in categorias[:3]) + f" (+{len(categorias) - 3} más)"


def _sanitizar_nombre_archivo(texto):
    return (
        str(texto).replace(' ', '_').replace('/', '-')
        .replace('$', '').replace(':', '')
    )


def render_facturacion():
    """Función principal del módulo de Facturación"""

    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())

    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)

    render_section_banner("💰", "Análisis de Facturación", rango_fechas)

    # =======================================================================
    # CARGAR DATOS
    # =======================================================================
    @st.cache_data(ttl=CACHE_TTL)
    def load_facturacion_detalle(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        try:
            df = db.execute_query(
                queries.get_facturacion_detalle_periodo(),
                {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            )
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None

        if df is None or df.empty:
            return df

        for col in ['Valor_Total', 'Valor_Copago', 'Valor_EAPB', 'Valor_Usuario']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        # Vectorizado (antes .apply fila a fila: lento con cientos de miles de filas)
        bordes = [r[0] for r in RANGOS_VALOR] + [float('inf')]
        df['Rango'] = pd.cut(
            df['Valor_Total'], bins=bordes, labels=[r[2] for r in RANGOS_VALOR],
            right=False
        ).astype(str)
        return df

    @st.cache_data(ttl=CACHE_TTL)
    def load_tendencias(f_inicio, f_fin):
        db = get_db_connector()
        query_tendencias = f"""
SELECT
    DATE(ef.FechFact)                                             AS Fecha,
    COUNT(DISTINCT CONCAT(ef.CodiInst, ef.CodiAno,
          ef.CodiDocu, ef.NumeFact))                              AS Total_Facturas,
    COALESCE(SUM(df.ValoTota), 0)                                AS Valor_Total,
    ROUND(
        COALESCE(SUM(df.ValoTota), 0)
        / NULLIF(COUNT(DISTINCT CONCAT(ef.CodiInst, ef.CodiAno,
          ef.CodiDocu, ef.NumeFact)), 0)
    , 0)                                                          AS Valor_Promedio,
    MAX(df.ValoTota)                                             AS Valor_Maximo,
    COUNT(DISTINCT fe.NumeDocu)                                  AS Facturas_Electronicas,
    COUNT(DISTINCT CASE WHEN fe.NumeDocu IS NULL
          THEN CONCAT(ef.CodiInst, ef.NumeFact) END)             AS Liquidaciones,
    COUNT(CASE WHEN ef.Anulado = 1 THEN 1 END)                   AS Facturas_Anuladas,
    ROUND(
        COUNT(CASE WHEN ef.Anulado = 1 THEN 1 END)
        / NULLIF(COUNT(*), 0) * 100
    , 1)                                                          AS Tasa_Anulacion
FROM EncaFact ef
JOIN DetaFact df
    ON  df.CodiInst = ef.CodiInst
    AND df.CodiAno  = ef.CodiAno
    AND df.CodiDocu = ef.CodiDocu
    AND df.NumeFact = ef.NumeFact
LEFT JOIN FactElec fe
    ON  fe.CodiInst = ef.CodiInst
    AND fe.CodiAno  = ef.CodiAno
    AND fe.NumeDocu = ef.NumeFact
    AND fe.CodiDocu = 'FE'
WHERE ef.FechFact BETWEEN '{f_inicio}' AND '{f_fin}'
GROUP BY DATE(ef.FechFact)
ORDER BY Fecha
"""
        return db.execute_query(query_tendencias)

    df = load_facturacion_detalle(fecha_inicio, fecha_fin)
    tendencias = load_tendencias(fecha_inicio, fecha_fin)

    if df is None:
        st.error("Error al cargar datos de facturación")
        st.stop()

    if df.empty:
        st.info("No hay datos de facturación para el período seleccionado")
        render_footer()
        return

    # Vistas reutilizadas en toda la pestaña
    df_activas = df[df['Anulado'] == 0]                                   # Causadas + Preliminares
    df_causadas = df[(df['Anulado'] == 0) & (df['Causado'] == 1)]
    df_pendientes = df[(df['Anulado'] == 0) & (df['Causado'] == 0)]
    df_anuladas = df[df['Anulado'] == 1]

    # =======================================================================
    # MÉTRICAS — separadas: Facturado (causado) vs Pendiente de Causar
    # =======================================================================
    render_heading_help(
        "💰 Facturado (causado contablemente)",
        "Liquidaciones con Causado=1: ya tienen su encabezado (EncaFact) completo, son "
        "las que cuentan como facturación en firme. El Valor Total sale de DetaFact "
        "(detalle real por ítem) para no depender del encabezado.",
        tag="h4"
    )
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "📄", "FACTURAS CAUSADAS", f"{len(df_causadas):,}",
            COLORS['primary'], COLORS['secondary'],
            help_text="Liquidaciones no anuladas y ya causadas (Causado=1) en el período."
        )
    with col2:
        render_metric_card(
            "💵", "VALOR TOTAL", f"${df_causadas['Valor_Total'].sum():,.0f}",
            COLORS['success'], COLORS['secondary'],
            help_text="Suma del valor real por ítem (DetaFact) de las liquidaciones causadas."
        )
    with col3:
        promedio = df_causadas['Valor_Total'].mean() if len(df_causadas) else 0
        render_metric_card(
            "📊", "PROMEDIO", f"${promedio:,.0f}",
            COLORS['info'], COLORS['secondary'],
            help_text="Valor Total / Facturas Causadas del período."
        )
    with col4:
        maximo = df_causadas['Valor_Total'].max() if len(df_causadas) else 0
        render_metric_card(
            "⬆️", "FACTURA MÁS ALTA", f"${maximo:,.0f}",
            COLORS['warning'], COLORS['secondary'],
            help_text="La liquidación causada de mayor valor en el período."
        )

    # Nota: se descarta ValoUsua ("Total a cargo del usuario") como tarjeta aparte —
    # verificado en vivo que es prácticamente idéntico a ValoCopa en el 99.99% de los
    # casos (789,982 de 790,091 liquidaciones históricas causadas), así que mostrar
    # ambos era información redundante.
    col5, col6 = st.columns(2)
    with col5:
        render_metric_card(
            "🧾", "COPAGO (USUARIO)", f"${df_causadas['Valor_Copago'].sum():,.0f}",
            COLORS['secondary'], COLORS['primary'],
            help_text="EncaFact.ValoCopa — cuotas/copagos a cargo del paciente. Solo se calcula "
                      "en liquidaciones ya causadas."
        )
    with col6:
        render_metric_card(
            "🏥", "COBRADO A EPS/EAPB", f"${df_causadas['Valor_EAPB'].sum():,.0f}",
            COLORS['info'], COLORS['primary'],
            help_text="EncaFact.ValoEAPB — valor cobrado a la entidad administradora (EPS/EAPB)."
        )

    render_section_divider()

    render_heading_help(
        "🕐 Pendiente de Causar",
        "Liquidaciones con Causado=0: ya tienen ítems en DetaFact, pero SIHOS aún no las "
        "'causa' contablemente y mientras tanto su encabezado (EncaFact) queda en $0. "
        "Mira la sección 'Por Facturador' para saber quién las tiene pendientes.",
        tag="h4"
    )
    colp1, colp2 = st.columns(2)
    with colp1:
        render_metric_card(
            "⏳", "LIQUIDACIONES PENDIENTES", f"{len(df_pendientes):,}",
            COLORS['warning'], COLORS['danger'],
            help_text="Liquidaciones no anuladas con Causado=0 en el período."
        )
    with colp2:
        render_metric_card(
            "💰", "VALOR PENDIENTE DE CAUSAR", f"${df_pendientes['Valor_Total'].sum():,.0f}",
            COLORS['danger'], COLORS['warning'],
            help_text="Suma del valor real por ítem (DetaFact) de esas liquidaciones — no "
                      "aparece en el encabezado EncaFact hasta que se causen."
        )

    render_section_divider()

    # =======================================================================
    # DISTRIBUCIÓN
    # =======================================================================
    render_section_banner(
        "📊", "Distribución de Facturación", rango_fechas,
        help_text="Servicio, Rangos y Tipo de Afiliación usan facturas no anuladas "
                  "(causadas + pendientes). Estado muestra las 3 categorías completas. "
                  "Haz clic en una porción/barra para ver el detalle de esas facturas abajo."
    )

    col_dist, col_grafica = st.columns([2, 2])

    with col_dist:
        opcion_dist = st.radio(
            "Ver distribución por:",
            ["Por Servicio", "Rangos de Valor", "Tipo de Afiliación", "Estado"],
            horizontal=True,
            key="radio_dist_facturacion"
        )

    with col_grafica:
        tipo_grafica_dist = st.radio(
            "Tipo de gráfica:",
            [
                "🥧 Pie Chart",
                "📊 Bar Horizontal",
                "📊 Bar Agrupadas",
                "☀️ Sunburst",
                "🌳 Treemap",
                "🗺️ Funnel"
            ],
            horizontal=True,
            key="radio_tipo_grafica_dist_fact"
        )

    if opcion_dist == "Por Servicio":
        base_dist = df_activas
        campo_filtro = 'Servicio'
        agg = base_dist.groupby('Servicio', as_index=False).agg(
            Total_Facturas=('NumeFact', 'count'), Valor_Total=('Valor_Total', 'sum'))
        agg = agg.sort_values('Valor_Total', ascending=False).head(10)
        campo_nombre, campo_valor, titulo = 'Servicio', 'Valor_Total', "Distribución por Servicio"
    elif opcion_dist == "Rangos de Valor":
        base_dist = df_activas
        campo_filtro = 'Rango'
        agg = base_dist.groupby('Rango', as_index=False).agg(
            Total_Facturas=('NumeFact', 'count'), Valor_Total=('Valor_Total', 'sum'))
        orden = [r[2] for r in RANGOS_VALOR]
        agg['_orden'] = agg['Rango'].apply(lambda x: orden.index(x) if x in orden else 99)
        agg = agg.sort_values('_orden').drop(columns='_orden')
        campo_nombre, campo_valor, titulo = 'Rango', 'Valor_Total', "Distribución por Rangos de Valor"
    elif opcion_dist == "Tipo de Afiliación":
        base_dist = df_activas
        campo_filtro = 'TipoAfiliacion'
        agg = base_dist.groupby('TipoAfiliacion', as_index=False).agg(
            Total_Facturas=('NumeFact', 'count'), Valor_Total=('Valor_Total', 'sum'))
        agg = agg.sort_values('Valor_Total', ascending=False)
        campo_nombre, campo_valor, titulo = 'TipoAfiliacion', 'Valor_Total', "Distribución por Tipo de Afiliación"
    else:  # Estado
        base_dist = df
        campo_filtro = 'Estado'
        agg = base_dist.groupby('Estado', as_index=False).agg(
            Total_Facturas=('NumeFact', 'count'), Valor_Total=('Valor_Total', 'sum'))
        orden_estado = {'Preliminar': 0, 'Causada': 1, 'Anulada': 2}
        agg['_orden'] = agg['Estado'].map(orden_estado).fillna(9)
        agg = agg.sort_values('_orden').drop(columns='_orden')
        campo_nombre, campo_valor, titulo = 'Estado', 'Valor_Total', "Distribución por Estado"

    datos_dist = agg
    seleccion_click = None

    if datos_dist is not None and not datos_dist.empty:
        col_graf, col_metricas = st.columns([3, 1])

        with col_graf:
            fig_dist = None

            if "Pie" in tipo_grafica_dist:
                fig_dist = px.pie(
                    datos_dist, values=campo_valor, names=campo_nombre, title=titulo,
                    custom_data=[campo_nombre], color_discrete_sequence=PALETA
                )
                fig_dist.update_traces(textposition='inside', textinfo='percent+label')

            elif "Bar Horizontal" in tipo_grafica_dist:
                fig_dist = px.bar(
                    datos_dist, x=campo_valor, y=campo_nombre, orientation='h', title=titulo,
                    color=campo_valor, color_continuous_scale='Blues', custom_data=[campo_nombre]
                )
                fig_dist.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)

            elif "Bar Agrupadas" in tipo_grafica_dist:
                fig_dist = px.bar(
                    datos_dist, x=campo_nombre, y=campo_valor, title=titulo,
                    color=campo_nombre, color_discrete_sequence=PALETA, custom_data=[campo_nombre]
                )
                fig_dist.update_layout(showlegend=False)

            elif "Sunburst" in tipo_grafica_dist:
                df_sunburst = datos_dist.copy()
                df_sunburst['Root'] = 'Total'
                fig_dist = px.sunburst(
                    df_sunburst, path=['Root', campo_nombre], values=campo_valor, title=titulo,
                    color_discrete_sequence=PALETA, custom_data=[campo_nombre]
                )

            elif "Treemap" in tipo_grafica_dist:
                fig_dist = px.treemap(
                    datos_dist, path=[campo_nombre], values=campo_valor, title=titulo,
                    color=campo_valor, color_continuous_scale='Blues', custom_data=[campo_nombre]
                )

            elif "Funnel" in tipo_grafica_dist:
                df_funnel = datos_dist.sort_values(campo_valor, ascending=False)
                fig_dist = px.funnel(
                    df_funnel, x=campo_valor, y=campo_nombre, title=titulo,
                    color_discrete_sequence=[COLORS['primary']], custom_data=[campo_nombre]
                )

            es_interactiva = any(t in tipo_grafica_dist for t in ("Bar Horizontal", "Bar Agrupadas"))
            st.session_state.setdefault('fact_dist_reset', 0)

            if fig_dist:
                fig_dist.update_layout(height=450)
                if es_interactiva:
                    evento_dist = st.plotly_chart(
                        fig_dist, use_container_width=True,
                        key=f"fig_dist_fact_{opcion_dist}_sel_{st.session_state['fact_dist_reset']}",
                        on_select="rerun", selection_mode=("points", "box")
                    )
                    seleccion_click = _extraer_click(evento_dist, campo_nombre)
                else:
                    st.plotly_chart(fig_dist, use_container_width=True, key=f"fig_dist_fact_{opcion_dist}_nosel")

                # Un único st.caption() SIEMPRE presente (solo cambia el texto) — evita
                # que Streamlit deje un elemento huérfano al alternar entre 0 y 1
                # captions condicionales de una corrida a otra (observado en vivo: un
                # <p> de "no interactiva" quedaba pegado tras pasar a Bar Horizontal).
                if es_interactiva:
                    st.caption(
                        "💡 Haz clic en una barra para ver el detalle de sus facturas abajo. "
                        "Multiselección: mantén Shift y haz clic en varias barras, o arrastra un recuadro."
                    )
                else:
                    st.caption(
                        "💡 Esta gráfica no admite clic para filtrar — es una limitación de Plotly: "
                        "Pie/Sunburst/Treemap/Funnel no emiten evento de selección al clic (solo Bar sí). "
                        "Cambia el 'Tipo de gráfica' a Bar Horizontal o Bar Agrupadas para el drill-down."
                    )

        with col_metricas:
            st.markdown("### 📊 Resumen")
            total = datos_dist[campo_valor].sum()
            st.metric("Total", f"${int(total):,}")

            top_3 = datos_dist.nlargest(3, campo_valor)
            st.markdown("#### 🏆 Top 3")
            for idx, row in top_3.iterrows():
                porcentaje = (row[campo_valor] / total * 100) if total else 0
                st.metric(
                    label=str(row[campo_nombre])[:25],
                    value=f"${int(row[campo_valor]):,}",
                    delta=f"{porcentaje:.1f}%"
                )

        # Una sola tabla interactiva: agregada por defecto, o el detalle de
        # facturas individuales de la categoría clicada en la gráfica de arriba.
        # El botón "Ver todo" reinicia también la gráfica (remonta el widget con
        # una key nueva) para que ambas vuelvan juntas a la vista general.
        st.markdown("---")
        col_tit, col_reset = st.columns([4, 1])
        if seleccion_click is not None:
            with col_tit:
                render_heading_help(
                    f"🔍 Facturas de: {_etiqueta_seleccion(seleccion_click)}",
                    "Detalle de facturas individuales de la(s) categoría(s) seleccionada(s) en la "
                    "gráfica de arriba. Vuelve a hacer clic en la misma barra, o usa "
                    "'Ver todo', para volver al resumen general.",
                    tag="h4"
                )
            with col_reset:
                if st.button("🔄 Ver todo", key=f"reset_dist_{opcion_dist}", use_container_width=True):
                    st.session_state['fact_dist_reset'] += 1
                    st.rerun()
            tabla_final = base_dist[base_dist[campo_filtro].isin(seleccion_click)][
                ['NumeFact', 'Fecha', 'Servicio', 'TipoAfiliacion', 'Estado',
                 'Valor_Total', 'Facturador']
            ].sort_values('Valor_Total', ascending=False)
            sufijo_archivo = f"detalle_{_sanitizar_nombre_archivo(_etiqueta_seleccion(seleccion_click))}"
        else:
            with col_tit:
                st.markdown("#### 📋 Resumen por categoría (agregado)")
            tabla_final = datos_dist
            sufijo_archivo = opcion_dist.lower().replace(' ', '_')

        st.dataframe(tabla_final, use_container_width=True, hide_index=True)

        colcsv, colxls = st.columns(2)
        with colcsv:
            st.download_button(
                "📥 Descargar CSV",
                data=tabla_final.to_csv(index=False, encoding='utf-8-sig'),
                file_name=f"facturacion_{sufijo_archivo}_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv", key=f"csv_dist_{opcion_dist}_{sufijo_archivo}"
            )
        with colxls:
            st.download_button(
                "📥 Descargar Excel",
                data=dataframe_to_excel(tabla_final),
                file_name=f"facturacion_{sufijo_archivo}_{fecha_inicio}_{fecha_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"xlsx_dist_{opcion_dist}_{sufijo_archivo}"
            )
    else:
        st.info(f"No hay datos disponibles para {opcion_dist}")

    render_section_divider()

    # =======================================================================
    # TENDENCIAS
    # =======================================================================
    render_section_banner("📈", "Tendencias en el Tiempo", rango_fechas)

    if tendencias is not None and not tendencias.empty:
        col_metrica, col_tipo = st.columns([2, 2])

        with col_metrica:
            metrica_tendencia = st.radio(
                "Métrica a visualizar:",
                [
                    "Valor Total Facturado",
                    "Cantidad de Facturas",
                    "Valor Promedio por Factura",
                    "Valor Máximo del Día",
                    "Facturas Electrónicas vs Liquidaciones",
                    "Tasa de Anulación"
                ],
                horizontal=True,
                key="radio_metrica_tendencia_fact"
            )

        with col_tipo:
            tipo_grafica = st.radio(
                "Tipo de gráfica:",
                [
                    "📈 Línea",
                    "📊 Barras",
                    "📉 Área",
                    "📊 Barras Apiladas",
                    "📈 Área Apilada",
                    "📊 Barras + Línea"
                ],
                horizontal=True,
                key="radio_tipo_grafica_fact"
            )

        fig_tendencia = None

        if metrica_tendencia == "Facturas Electrónicas vs Liquidaciones":
            if "Área" in tipo_grafica and ("Apilada" in tipo_grafica or "Apiladas" in tipo_grafica):
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=tendencias['Fecha'], y=tendencias['Facturas_Electronicas'],
                    name='Facturas Electrónicas', fill='tonexty', mode='lines',
                    line=dict(color=COLORS['primary'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=tendencias['Fecha'], y=tendencias['Liquidaciones'],
                    name='Liquidaciones', fill='tonexty', mode='lines',
                    line=dict(color=COLORS['info'])
                ))
                fig_tendencia.update_layout(title="Facturas Electrónicas vs Liquidaciones", height=450)
            elif "Apiladas" in tipo_grafica or "Apilada" in tipo_grafica:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Bar(
                    x=tendencias['Fecha'], y=tendencias['Facturas_Electronicas'],
                    name='Facturas Electrónicas', marker_color=COLORS['primary']
                ))
                fig_tendencia.add_trace(go.Bar(
                    x=tendencias['Fecha'], y=tendencias['Liquidaciones'],
                    name='Liquidaciones', marker_color=COLORS['info']
                ))
                fig_tendencia.update_layout(barmode='stack', title="Facturas Electrónicas vs Liquidaciones", height=450)
            else:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=tendencias['Fecha'], y=tendencias['Facturas_Electronicas'],
                    mode='lines+markers', name='Facturas Electrónicas',
                    line=dict(color=COLORS['primary'], width=2)
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=tendencias['Fecha'], y=tendencias['Liquidaciones'],
                    mode='lines+markers', name='Liquidaciones',
                    line=dict(color=COLORS['info'], width=2)
                ))
                fig_tendencia.update_layout(title="Facturas Electrónicas vs Liquidaciones", height=450, hovermode='x unified')

        else:
            if metrica_tendencia == "Valor Total Facturado":
                campo_y, titulo, color = 'Valor_Total', "Valor Total Facturado", COLORS['success']
            elif metrica_tendencia == "Cantidad de Facturas":
                campo_y, titulo, color = 'Total_Facturas', "Cantidad de Facturas", COLORS['primary']
            elif metrica_tendencia == "Valor Promedio por Factura":
                campo_y, titulo, color = 'Valor_Promedio', "Valor Promedio por Factura", COLORS['info']
            elif metrica_tendencia == "Valor Máximo del Día":
                campo_y, titulo, color = 'Valor_Maximo', "Valor Máximo del Día", COLORS['warning']
            else:
                campo_y, titulo, color = 'Tasa_Anulacion', "Tasa de Anulación (%)", COLORS['danger']

            if "Línea" in tipo_grafica and "Barras" not in tipo_grafica:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=tendencias['Fecha'], y=tendencias[campo_y],
                    mode='lines+markers', name=titulo,
                    line=dict(color=color, width=3), marker=dict(size=10),
                    fill='tozeroy',
                    fillcolor=f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.2)"
                ))
                fig_tendencia.update_layout(title=titulo, height=450, hovermode='x unified')

            elif tipo_grafica == "📊 Barras":
                fig_tendencia = px.bar(
                    tendencias, x='Fecha', y=campo_y, title=titulo,
                    color=campo_y, color_continuous_scale='Blues'
                )
                fig_tendencia.update_layout(height=450, showlegend=False)

            elif tipo_grafica == "📉 Área":
                fig_tendencia = px.area(
                    tendencias, x='Fecha', y=campo_y, title=titulo,
                    color_discrete_sequence=[color]
                )
                fig_tendencia.update_layout(height=450)

        if fig_tendencia:
            st.plotly_chart(fig_tendencia, use_container_width=True, key="fig_tendencia_fact")

        st.markdown("### 📊 Resumen del Período")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total = tendencias['Valor_Total'].sum()
            st.metric("Total Facturado", f"${int(total):,}")

        with col2:
            promedio = tendencias['Valor_Total'].mean()
            st.metric("Promedio Diario", f"${int(promedio):,}")

        with col3:
            dia_max = tendencias.loc[tendencias['Valor_Total'].idxmax()]
            st.metric("Día Máximo", f"${int(dia_max['Valor_Total']):,}", delta=dia_max['Fecha'].strftime('%d/%m'))

        with col4:
            total_facturas = tendencias['Total_Facturas'].sum()
            st.metric("Total Facturas", f"{int(total_facturas):,}")

    else:
        st.info("No hay datos de tendencias para el período seleccionado")

    render_section_divider()

    # =======================================================================
    # POR FACTURADOR
    # =======================================================================
    render_section_banner(
        "👤", "Por Facturador", rango_fechas,
        help_text="'Facturador' = quién digitó la liquidación (UsuaDigi). En Anulaciones se "
                  "agrupa por quién ejecutó la anulación (UsuaAnul), que puede ser otra persona."
    )

    vista_facturador = st.radio(
        "Ver:",
        ["Distribución de Facturas", "Anulaciones", "Pendientes de Causar"],
        horizontal=True, key="radio_vista_facturador"
    )

    if vista_facturador == "Distribución de Facturas":
        base_f = df_activas
        campo_agrup = 'Facturador'
        titulo_f = "Facturas por Facturador"
        columnas_detalle = ['NumeFact', 'Fecha', 'Servicio', 'TipoAfiliacion', 'Estado', 'Valor_Total', 'Facturador']
    elif vista_facturador == "Anulaciones":
        base_f = df_anuladas
        campo_agrup = 'Anulador'
        titulo_f = "Anulaciones Realizadas por Facturador"
        columnas_detalle = ['NumeFact', 'Fecha', 'FechaAnulacion', 'Servicio', 'Valor_Total',
                            'Facturador', 'Anulador', 'CausaAnulacion', 'MotivoAnulacion']
    else:  # Pendientes de Causar
        base_f = df_pendientes
        campo_agrup = 'Facturador'
        titulo_f = "Liquidaciones Pendientes de Causar por Facturador"
        columnas_detalle = ['NumeFact', 'Fecha', 'Servicio', 'TipoAfiliacion', 'Valor_Total', 'Facturador']

    if not base_f.empty:
        agg_f = base_f.groupby(campo_agrup, as_index=False).agg(
            Total_Facturas=('NumeFact', 'count'), Valor_Total=('Valor_Total', 'sum')
        ).sort_values('Total_Facturas', ascending=False)

        n_facturadores = len(agg_f)
        if n_facturadores > 5:
            # Tope dinámico = total de facturadores (antes fijo en 30, y hay ~43).
            top_n_f = st.slider(
                f"Cantidad de facturadores a mostrar (hay {n_facturadores}):",
                min_value=5, max_value=n_facturadores, value=min(15, n_facturadores), step=1,
                key=f"slider_top_facturador_{vista_facturador}"
            )
        else:
            top_n_f = n_facturadores
        agg_mostrar = agg_f.head(top_n_f)

        fig_f = px.bar(
            agg_mostrar, x='Total_Facturas', y=campo_agrup, orientation='h',
            color='Valor_Total', color_continuous_scale='Blues', title=titulo_f,
            hover_data=['Valor_Total'], custom_data=[campo_agrup]
        )
        fig_f.update_layout(
            height=max(400, len(agg_mostrar) * 30),
            yaxis={'categoryorder': 'total ascending'}
        )
        st.session_state.setdefault('fact_facturador_reset', 0)
        evento_f = st.plotly_chart(
            fig_f, use_container_width=True,
            key=f"fig_facturador_{vista_facturador}_{st.session_state['fact_facturador_reset']}",
            on_select="rerun", selection_mode=("points", "box")
        )
        facturador_click = _extraer_click(evento_f, campo_agrup)
        st.caption(
            "💡 Haz clic en una barra para ver el detalle de sus facturas. "
            "Multiselección: mantén Shift y haz clic en varias barras, o arrastra un recuadro."
        )

        sufijo = vista_facturador.lower().replace(' ', '_')

        # Una sola tabla interactiva: agregada por defecto, o el detalle de
        # facturas del facturador clicado en la gráfica de arriba.
        col_tit_f, col_reset_f = st.columns([4, 1])
        if facturador_click is not None:
            with col_tit_f:
                render_heading_help(
                    f"🔍 Facturas de: {_etiqueta_seleccion(facturador_click)}",
                    "Detalle de facturas individuales de la(s) persona(s) seleccionada(s) en la "
                    "gráfica de arriba. Vuelve a hacer clic en la misma barra, o usa "
                    "'Ver todo', para volver al resumen general.",
                    tag="h4"
                )
            with col_reset_f:
                if st.button("🔄 Ver todo", key=f"reset_facturador_{vista_facturador}", use_container_width=True):
                    st.session_state['fact_facturador_reset'] += 1
                    st.rerun()
            tabla_final_f = base_f[base_f[campo_agrup].isin(facturador_click)][columnas_detalle] \
                .sort_values('Fecha', ascending=False)
            sufijo_archivo_f = f"{sufijo}_{_sanitizar_nombre_archivo(_etiqueta_seleccion(facturador_click))}"
        else:
            with col_tit_f:
                st.markdown(f"#### 📋 {titulo_f} (tabla de la gráfica)")
            tabla_final_f = agg_mostrar.rename(columns={campo_agrup: 'Facturador'})
            sufijo_archivo_f = f"{sufijo}_resumen"

        st.dataframe(tabla_final_f, use_container_width=True, hide_index=True)

        colcsv_f, colxls_f = st.columns(2)
        with colcsv_f:
            st.download_button(
                "📥 Descargar CSV",
                data=tabla_final_f.to_csv(index=False, encoding='utf-8-sig'),
                file_name=f"facturador_{sufijo_archivo_f}_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv", key=f"csv_facturador_{vista_facturador}_{sufijo_archivo_f}"
            )
        with colxls_f:
            st.download_button(
                "📥 Descargar Excel",
                data=dataframe_to_excel(tabla_final_f),
                file_name=f"facturador_{sufijo_archivo_f}_{fecha_inicio}_{fecha_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"xlsx_facturador_{vista_facturador}_{sufijo_archivo_f}"
            )
    else:
        st.info(f"No hay datos para '{vista_facturador}' en el período seleccionado")

    render_footer()

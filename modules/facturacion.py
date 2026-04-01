"""
Módulo Facturación - Análisis Completo
Sigue el patrón de Admisiones con:
- Distribución con 6 opciones y 6 tipos de gráficas
- Tendencias con 6 métricas y 6 tipos de gráficas
- Secciones adicionales específicas
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
    render_section_divider
)
from components.layout import render_footer

def render_facturacion():
    """Función principal del módulo de Facturación"""

    # Obtener filtros del sidebar
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)
    
    render_section_banner("💰", "Análisis de Facturación", rango_fechas)
    
    # =======================================================================
    # CARGAR DATOS
    # =======================================================================
    @st.cache_data(ttl=CACHE_TTL)
    def load_facturacion_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            
            # Estadísticas
            data['estadisticas'] = db.execute_query(
                queries.get_estadisticas_facturacion(), params
            )
            
            # Distribución (6 opciones)
            data['por_rango'] = db.execute_query(
                queries.get_facturacion_por_rango(), params
            )
            data['por_tipo_afiliacion'] = db.execute_query(
                queries.get_facturacion_por_tipo_afiliacion(), params
            )
            data['por_servicio'] = db.execute_query(
                queries.get_facturacion_por_servicio(), params
            )
            data['por_tipo_documento'] = db.execute_query(
                queries.get_facturacion_por_tipo_documento(), params
            )
            data['por_estado'] = db.execute_query(
                queries.get_facturacion_por_estado(), params
            )
            data['por_mes'] = db.execute_query(
                queries.get_facturacion_por_mes(), params
            )
            
            # Tendencias (agregación diaria para gráficas)
            query_tendencias = f"""
            SELECT 
                DATE(FechFact) as Fecha,
                COUNT(*) as Total_Facturas,
                SUM(ValoTota) as Valor_Total,
                AVG(ValoTota) as Valor_Promedio,
                MAX(ValoTota) as Valor_Maximo,
                COUNT(CASE WHEN CodiDocu = 'FE' THEN 1 END) as Facturas_Electronicas,
                COUNT(CASE WHEN CodiDocu = 'LIQ' THEN 1 END) as Liquidaciones,
                COUNT(CASE WHEN Anulado = 1 THEN 1 END) as Facturas_Anuladas,
                ROUND((COUNT(CASE WHEN Anulado = 1 THEN 1 END) / COUNT(*)) * 100, 1) as Tasa_Anulacion
            FROM EncaFact
            WHERE FechFact BETWEEN '{f_inicio}' AND '{f_fin}'
            GROUP BY DATE(FechFact)
            ORDER BY Fecha
            """
            data['tendencias'] = db.execute_query(query_tendencias)
            
            # Secciones adicionales
            data['top_facturas'] = db.execute_query(
                queries.get_top_facturas_altas(), params
            )
            data['analisis_cartera'] = db.execute_query(
                queries.get_analisis_cartera(), params
            )
            data['indicadores_recaudo'] = db.execute_query(
                queries.get_indicadores_recaudo(), params
            )
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None
        
        return data
    
    data = load_facturacion_data(fecha_inicio, fecha_fin)
    
    if data is None:
        st.error("Error al cargar datos de facturación")
        st.stop()
    
    # =======================================================================
    # MÉTRICAS PRINCIPALES
    # =======================================================================
    if not data['estadisticas'].empty:
        stats = data['estadisticas'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = int(stats.get('Total_Facturas', 0))
            render_metric_card(
                "📄",
                "TOTAL FACTURAS",
                f"{total:,}",
                COLORS['primary'],
                COLORS['secondary']
            )
        
        with col2:
            valor = float(stats.get('Valor_Total', 0))
            render_metric_card(
                "💵",
                "VALOR TOTAL",
                f"${valor:,.0f}",
                COLORS['success'],
                COLORS['secondary']
            )
        
        with col3:
            promedio = float(stats.get('Valor_Promedio', 0))
            render_metric_card(
                "📊",
                "PROMEDIO",
                f"${promedio:,.0f}",
                COLORS['info'],
                COLORS['secondary']
            )
        
        with col4:
            maximo = float(stats.get('Valor_Maximo', 0))
            render_metric_card(
                "⬆️",
                "FACTURA MÁS ALTA",
                f"${maximo:,.0f}",
                COLORS['warning'],
                COLORS['secondary']
            )
    
    render_section_divider()
    
    # =======================================================================
    # DISTRIBUCIÓN
    # =======================================================================
    render_section_banner("📊", "Distribución de Facturación", rango_fechas)
    
    # Fila 1: Radio buttons
    col_dist, col_grafica = st.columns([2, 2])
    
    with col_dist:
        opcion_dist = st.radio(
            "Ver distribución por:",
            [
                "Por Servicio",
                "Rangos de Valor",
                "Tipo de Afiliación",
                "Tipo de Documento",
                "Estado",
                "Mes"
            ],
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
    
    # Seleccionar datos según opción
    datos_dist = None
    campo_nombre = None
    campo_valor = None
    titulo = None
    
    if opcion_dist == "Rangos de Valor":
        datos_dist = data['por_rango']
        campo_nombre = 'Rango'
        campo_valor = 'Total'
        titulo = "Distribución por Rangos de Valor"
    elif opcion_dist == "Tipo de Afiliación":
        datos_dist = data['por_tipo_afiliacion']
        campo_nombre = 'Tipo'
        campo_valor = 'Valor_Total'
        titulo = "Distribución por Tipo de Afiliación"
    elif opcion_dist == "Por Servicio":
        datos_dist = data['por_servicio']
        campo_nombre = 'Servicio'
        campo_valor = 'Valor_Total'
        titulo = "Distribución por Servicio"
    elif opcion_dist == "Tipo de Documento":
        datos_dist = data['por_tipo_documento']
        campo_nombre = 'Tipo_Documento'
        campo_valor = 'Valor_Total'
        titulo = "Distribución por Tipo de Documento"
    elif opcion_dist == "Estado":
        datos_dist = data['por_estado']
        campo_nombre = 'Estado'
        campo_valor = 'Valor_Total'
        titulo = "Distribución por Estado"
    else:  # Mes
        datos_dist = data['por_mes']
        campo_nombre = 'Mes_Nombre'
        campo_valor = 'Valor_Total'
        titulo = "Distribución por Mes"
    
    if datos_dist is not None and not datos_dist.empty:
        # Fila 2: Gráfica (75%) + Métricas (25%)
        col_graf, col_metricas = st.columns([3, 1])
        
        with col_graf:
            fig_dist = None
            
            if "Pie" in tipo_grafica_dist:
                fig_dist = px.pie(
                    datos_dist,
                    values=campo_valor,
                    names=campo_nombre,
                    title=titulo,
                    color_discrete_sequence=[
                        COLORS['primary'], COLORS['info'], COLORS['success'],
                        COLORS['warning'], COLORS['secondary'], COLORS['danger'],
                        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#96CEB4'
                    ]
                )
                fig_dist.update_traces(textposition='inside', textinfo='percent+label')
            
            elif "Bar Horizontal" in tipo_grafica_dist:
                fig_dist = px.bar(
                    datos_dist,
                    x=campo_valor,
                    y=campo_nombre,
                    orientation='h',
                    title=titulo,
                    color=campo_valor,
                    color_continuous_scale='Blues'
                )
                fig_dist.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            
            elif "Bar Agrupadas" in tipo_grafica_dist:
                fig_dist = px.bar(
                    datos_dist,
                    x=campo_nombre,
                    y=campo_valor,
                    title=titulo,
                    color=campo_nombre,
                    color_discrete_sequence=[
                        COLORS['primary'], COLORS['info'], COLORS['success'],
                        COLORS['warning'], COLORS['secondary'], COLORS['danger']
                    ]
                )
                fig_dist.update_layout(showlegend=False)
            
            elif "Sunburst" in tipo_grafica_dist:
                df_sunburst = datos_dist.copy()
                df_sunburst['Root'] = 'Total'
                fig_dist = px.sunburst(
                    df_sunburst,
                    path=['Root', campo_nombre],
                    values=campo_valor,
                    title=titulo,
                    color_discrete_sequence=[
                        COLORS['primary'], COLORS['info'], COLORS['success'],
                        COLORS['warning'], COLORS['secondary'], COLORS['danger']
                    ]
                )
            
            elif "Treemap" in tipo_grafica_dist:
                fig_dist = px.treemap(
                    datos_dist,
                    path=[campo_nombre],
                    values=campo_valor,
                    title=titulo,
                    color=campo_valor,
                    color_continuous_scale='Blues'
                )
            
            elif "Funnel" in tipo_grafica_dist:
                df_funnel = datos_dist.sort_values(campo_valor, ascending=False)
                fig_dist = px.funnel(
                    df_funnel,
                    x=campo_valor,
                    y=campo_nombre,
                    title=titulo,
                    color_discrete_sequence=[COLORS['primary']]
                )
            
            if fig_dist:
                fig_dist.update_layout(height=450)
                st.plotly_chart(fig_dist, use_container_width=True)
        
        with col_metricas:
            st.markdown("### 📊 Resumen")
            total = datos_dist[campo_valor].sum()
            st.metric("Total", f"${int(total):,}")
            
            # Top 3
            top_3 = datos_dist.nlargest(3, campo_valor)
            st.markdown("#### 🏆 Top 3")
            for idx, row in top_3.iterrows():
                porcentaje = (row[campo_valor] / total) * 100
                st.metric(
                    label=str(row[campo_nombre])[:25],
                    value=f"${int(row[campo_valor]):,}",
                    delta=f"{porcentaje:.1f}%"
                )
        
        # Fila 3: Tabla en Expander
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(datos_dist, use_container_width=True, hide_index=True)
            
            csv = datos_dist.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"facturacion_{opcion_dist.lower().replace(' ', '_')}_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
    else:
        st.info(f"No hay datos disponibles para {opcion_dist}")
    
    render_section_divider()
    
    # =======================================================================
    # TENDENCIAS
    # =======================================================================
    render_section_banner("📈", "Tendencias en el Tiempo", rango_fechas)
    
    if not data['tendencias'].empty:
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
        
        # Crear gráfica
        fig_tendencia = None
        
        if metrica_tendencia == "Facturas Electrónicas vs Liquidaciones":
            # Gráfica múltiple
            if "Área" in tipo_grafica and ("Apilada" in tipo_grafica or "Apiladas" in tipo_grafica):
                # Crear como Scatter desde el inicio para Área Apilada
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Facturas_Electronicas'],
                    name='Facturas Electrónicas',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['primary'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Liquidaciones'],
                    name='Liquidaciones',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['info'])
                ))
                fig_tendencia.update_layout(title="Facturas Electrónicas vs Liquidaciones", height=450)
            elif "Apiladas" in tipo_grafica or "Apilada" in tipo_grafica:
                # Barras Apiladas
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Facturas_Electronicas'],
                    name='Facturas Electrónicas',
                    marker_color=COLORS['primary']
                ))
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Liquidaciones'],
                    name='Liquidaciones',
                    marker_color=COLORS['info']
                ))
                fig_tendencia.update_layout(barmode='stack', title="Facturas Electrónicas vs Liquidaciones", height=450)
            else:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Facturas_Electronicas'],
                    mode='lines+markers',
                    name='Facturas Electrónicas',
                    line=dict(color=COLORS['primary'], width=2)
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Liquidaciones'],
                    mode='lines+markers',
                    name='Liquidaciones',
                    line=dict(color=COLORS['info'], width=2)
                ))
                fig_tendencia.update_layout(title="Facturas Electrónicas vs Liquidaciones", height=450, hovermode='x unified')
        
        else:
            # Gráfica simple
            if metrica_tendencia == "Valor Total Facturado":
                campo_y = 'Valor_Total'
                titulo = "Valor Total Facturado"
                color = COLORS['success']
            elif metrica_tendencia == "Cantidad de Facturas":
                campo_y = 'Total_Facturas'
                titulo = "Cantidad de Facturas"
                color = COLORS['primary']
            elif metrica_tendencia == "Valor Promedio por Factura":
                campo_y = 'Valor_Promedio'
                titulo = "Valor Promedio por Factura"
                color = COLORS['info']
            elif metrica_tendencia == "Valor Máximo del Día":
                campo_y = 'Valor_Maximo'
                titulo = "Valor Máximo del Día"
                color = COLORS['warning']
            else:  # Tasa de Anulación
                campo_y = 'Tasa_Anulacion'
                titulo = "Tasa de Anulación (%)"
                color = COLORS['danger']
            
            if "Línea" in tipo_grafica and "Barras" not in tipo_grafica:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias'][campo_y],
                    mode='lines+markers',
                    name=titulo,
                    line=dict(color=color, width=3),
                    marker=dict(size=10),
                    fill='tozeroy',
                    fillcolor=f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.2)"
                ))
                fig_tendencia.update_layout(title=titulo, height=450, hovermode='x unified')
            
            elif tipo_grafica == "📊 Barras":
                fig_tendencia = px.bar(
                    data['tendencias'],
                    x='Fecha',
                    y=campo_y,
                    title=titulo,
                    color=campo_y,
                    color_continuous_scale='Blues'
                )
                fig_tendencia.update_layout(height=450, showlegend=False)
            
            elif tipo_grafica == "📉 Área":
                fig_tendencia = px.area(
                    data['tendencias'],
                    x='Fecha',
                    y=campo_y,
                    title=titulo,
                    color_discrete_sequence=[color]
                )
                fig_tendencia.update_layout(height=450)
        
        if fig_tendencia:
            st.plotly_chart(fig_tendencia, use_container_width=True)
        
        # Métricas resumen
        st.markdown("### 📊 Resumen del Período")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = data['tendencias']['Valor_Total'].sum()
            st.metric("Total Facturado", f"${int(total):,}")
        
        with col2:
            promedio = data['tendencias']['Valor_Total'].mean()
            st.metric("Promedio Diario", f"${int(promedio):,}")
        
        with col3:
            dia_max = data['tendencias'].loc[data['tendencias']['Valor_Total'].idxmax()]
            st.metric("Día Máximo", f"${int(dia_max['Valor_Total']):,}", delta=dia_max['Fecha'].strftime('%d/%m'))
        
        with col4:
            total_facturas = data['tendencias']['Total_Facturas'].sum()
            st.metric("Total Facturas", f"{int(total_facturas):,}")
    
    else:
        st.info("No hay datos de tendencias para el período seleccionado")
    
    render_section_divider()
    
    # =======================================================================
    # TOP FACTURAS MÁS ALTAS
    # =======================================================================
    render_section_banner("💰", "Top Facturas Más Altas", rango_fechas)
    
    if not data['top_facturas'].empty:
        # Control de visualización con Selectbox
        opciones_top = ['Top 10', 'Top 20', 'Top 50', 'Mostrar Todos']
        seleccion_top = st.selectbox(
            "Cantidad a mostrar:",
            opciones_top,
            key="select_top_facturas"
        )

        # Determinar cuántos mostrar
        if seleccion_top == 'Top 10':
            datos_mostrar = data['top_facturas'].head(10)
        elif seleccion_top == 'Top 20':
            datos_mostrar = data['top_facturas'].head(20)
        elif seleccion_top == 'Top 50':
            datos_mostrar = data['top_facturas'].head(50)
        else:
            datos_mostrar = data['top_facturas']
        
        fig = px.bar(
            datos_mostrar,
            x='Valor_Total',
            y='Numero_Factura',
            orientation='v',
            color='Valor_Total',
            color_continuous_scale='Greens',
            hover_data=['Servicio', 'Tipo_Afiliacion', 'Fecha'],
            title=f"{seleccion_top} Facturas Más Altas"
        )
        fig.update_layout(
            height=max(400, len(datos_mostrar) * 20),
            yaxis={'categoryorder':'total ascending'},
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(datos_mostrar, use_container_width=True, hide_index=True)
            
            csv = datos_mostrar.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"top_facturas_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
        
    else:
        st.info("No hay datos de facturas")
    
    render_footer()

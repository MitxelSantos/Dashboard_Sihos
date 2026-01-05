"""
Módulo Facturación - Análisis Completo con Radio Buttons y Nuevas Secciones
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
    
    render_section_banner("💰", "Análisis de Facturación")
    
    # Obtener filtros del sidebar
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)
    st.markdown(f"<div style='text-align: center; color: #6c757d; font-size: 0.85rem; margin-top: -10px; margin-bottom: 15px;'>{rango_fechas}</div>", unsafe_allow_html=True)
    
    # Cargar datos
    @st.cache_data(ttl=CACHE_TTL)
    def load_facturacion_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            
            data['estadisticas'] = db.execute_query(
                queries.get_estadisticas_facturacion(), params
            )
            
            # Distribución con 6 opciones
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
            
            # Nuevas secciones
            data['top_facturas_altas'] = db.execute_query(
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
    # DISTRIBUCIÓN DE FACTURACIÓN (RADIO BUTTONS)
    # =======================================================================
    render_section_banner("📊", "Distribución de Facturación", rango_fechas)
    
    # Radio buttons con 6 opciones
    vista_dist = st.radio(
        "Ver distribución por:",
        ["Rangos de Valor", "Tipo de Afiliación", "Por Servicio", "Tipo de Documento", "Estado", "Mes"],
        horizontal=False,
        key="radio_dist_facturacion"
    )
    
    # Seleccionar datos según opción
    if vista_dist == "Rangos de Valor":
        datos_dist = data['por_rango']
        campo_valor = 'Total'
        campo_nombre = 'Rango'
        titulo = "Distribución por Rangos de Valor"
    elif vista_dist == "Tipo de Afiliación":
        datos_dist = data['por_tipo_afiliacion']
        campo_valor = 'Valor_Total'
        campo_nombre = 'Tipo'
        titulo = "Distribución por Tipo de Afiliación"
    elif vista_dist == "Por Servicio":
        datos_dist = data['por_servicio']
        campo_valor = 'Valor_Total'
        campo_nombre = 'Servicio'
        titulo = "Distribución por Servicio"
    elif vista_dist == "Tipo de Documento":
        datos_dist = data['por_tipo_documento']
        campo_valor = 'Valor_Total'
        campo_nombre = 'Tipo_Documento'
        titulo = "Distribución por Tipo de Documento"
    elif vista_dist == "Estado":
        datos_dist = data['por_estado']
        campo_valor = 'Valor_Total'
        campo_nombre = 'Estado'
        titulo = "Distribución por Estado"
    else:  # Mes
        datos_dist = data['por_mes']
        campo_valor = 'Valor_Total'
        campo_nombre = 'Mes_Nombre'
        titulo = "Distribución por Mes"
    
    if not datos_dist.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # PIE CHART
            fig_pie = px.pie(
                datos_dist,
                values=campo_valor,
                names=campo_nombre,
                title=titulo,
                color_discrete_sequence=[
                    COLORS['primary'], COLORS['info'], COLORS['success'],
                    COLORS['warning'], COLORS['secondary'], COLORS['danger'],
                    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'
                ]
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # BAR CHART HORIZONTAL
            fig_bar = px.bar(
                datos_dist,
                x=campo_valor,
                y=campo_nombre,
                orientation='h',
                title=f"{titulo} - Comparativa",
                color_discrete_sequence=[COLORS['primary']]
            )
            fig_bar.update_layout(
                height=400,
                yaxis={'categoryorder':'total ascending'},
                xaxis_title="Valor Total",
                yaxis_title=""
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # TABLA DETALLADA
        st.markdown("### 📋 Tabla Detallada")
        st.dataframe(datos_dist, use_container_width=True, hide_index=True)
    else:
        st.info(f"No hay datos para {vista_dist}")
    
    render_section_divider()
    
    # =======================================================================
    # TOP FACTURAS MÁS ALTAS
    # =======================================================================
    render_section_banner("💰", "Top Facturas Más Altas", rango_fechas)
    
    if not data['top_facturas_altas'].empty:
        # Slider
        top_n = st.slider(
            "Cantidad a mostrar:",
            min_value=10,
            max_value=100,
            value=20,
            step=10,
            key="slider_top_facturas"
        )
        
        datos_mostrar = data['top_facturas_altas'] if top_n == 100 else data['top_facturas_altas'].head(top_n)
        
        # Gráfico de barras horizontal
        fig = px.bar(
            datos_mostrar,
            x='Valor_Total',
            y='Numero_Factura',
            orientation='h',
            color='Valor_Total',
            color_continuous_scale='Reds',
            hover_data=['Servicio', 'Tipo_Afiliacion', 'Fecha'],
            title=f"Top {top_n if top_n < 100 else 'Todas las'} Facturas Más Altas"
        )
        fig.update_layout(
            height=max(400, len(datos_mostrar) * 20),
            yaxis={'categoryorder':'total ascending'},
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla detallada
        st.markdown("### 📋 Detalle de Facturas")
        st.dataframe(
            datos_mostrar[['Numero_Factura', 'Fecha', 'Servicio', 'Tipo_Afiliacion', 'Valor_Total']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de facturas")
    
    render_section_divider()
    
    # =======================================================================
    # ANÁLISIS DE CARTERA
    # =======================================================================
    render_section_banner("📊", "Análisis de Facturación", rango_fechas)
    
    if not data['analisis_cartera'].empty:
        cartera = data['analisis_cartera'].iloc[0]
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Facturas",
                f"{int(cartera.get('Total_Facturas', 0)):,}"
            )
        
        with col2:
            st.metric(
                "Valor Total Facturado",
                f"${cartera.get('Valor_Total_Facturado', 0):,.0f}"
            )
        
        with col3:
            st.metric(
                "Facturas Electrónicas",
                f"{int(cartera.get('Facturas_Electronicas', 0)):,}"
            )
        
        with col4:
            st.metric(
                "Liquidaciones",
                f"{int(cartera.get('Liquidaciones', 0)):,}"
            )
        
        # Gráfico comparativo
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribución por tipo de documento
            tipos_doc = pd.DataFrame({
                'Tipo': ['Facturas Electrónicas', 'Liquidaciones'],
                'Cantidad': [
                    int(cartera.get('Facturas_Electronicas', 0)),
                    int(cartera.get('Liquidaciones', 0))
                ]
            })
            
            fig1 = px.pie(
                tipos_doc,
                values='Cantidad',
                names='Tipo',
                title="Distribución por Tipo de Documento",
                color_discrete_sequence=[COLORS['primary'], COLORS['info']]
            )
            fig1.update_traces(textposition='inside', textinfo='percent+label+value')
            fig1.update_layout(height=300)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Comparativa de valores
            fig2 = go.Figure(data=[
                go.Bar(
                    name='Valor Promedio',
                    x=['Facturación'],
                    y=[cartera.get('Valor_Promedio_Factura', 0)],
                    marker_color=COLORS['info']
                ),
                go.Bar(
                    name='Facturas Altas (>1M)',
                    x=['Facturación'],
                    y=[cartera.get('Valor_Facturas_Altas', 0)],
                    marker_color=COLORS['danger']
                )
            ])
            fig2.update_layout(
                title="Análisis de Valores",
                barmode='group',
                height=300
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No hay datos de análisis de cartera")
    
    render_section_divider()
    
    # =======================================================================
    # INDICADORES DE FACTURACIÓN POR SERVICIO
    # =======================================================================
    render_section_banner("💳", "Indicadores de Facturación por Servicio", rango_fechas)
    
    if not data['indicadores_recaudo'].empty:
        # Top 10 servicios por facturación
        top_10 = data['indicadores_recaudo'].head(10)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Valor total por servicio
            fig1 = px.bar(
                top_10,
                x='Valor_Total',
                y='Servicio',
                orientation='h',
                color='Valor_Total',
                color_continuous_scale='Blues',
                title="Top 10 Servicios - Valor Total"
            )
            fig1.update_layout(
                height=400,
                yaxis={'categoryorder':'total ascending'},
                showlegend=False
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Valor promedio por factura
            fig2 = px.bar(
                top_10,
                x='Valor_Promedio',
                y='Servicio',
                orientation='h',
                color='Valor_Promedio',
                color_continuous_scale='Greens',
                title="Top 10 Servicios - Valor Promedio por Factura"
            )
            fig2.update_layout(
                height=400,
                yaxis={'categoryorder':'total ascending'},
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Tabla completa con todos los datos
        st.markdown("### 📋 Tabla Detallada - Todos los Servicios")
        st.dataframe(
            data['indicadores_recaudo'],
            use_container_width=True,
            hide_index=True,
            height=400
        )
    else:
        st.info("No hay datos de indicadores por servicio")
    
    # Footer
    render_footer()

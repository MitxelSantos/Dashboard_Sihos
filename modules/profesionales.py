"""
Módulo Profesionales - Análisis Completo de Productividad y Carga
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
    render_metric_card,
    render_section_banner,
    render_section_divider
)
from components.layout import render_footer

def render_profesionales():
    """Función principal del módulo de Profesionales"""
    
    render_section_banner("👨‍⚕️", "Análisis de Atenciones por Profesional")
    
    # Obtener filtros del sidebar
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    # Cargar datos
    @st.cache_data(ttl=CACHE_TTL)
    def load_profesionales_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            
            data['estadisticas'] = db.execute_query(
                queries.get_estadisticas_profesionales(), params
            )
            data['top_profesionales'] = db.execute_query(
                queries.get_top_profesionales(), params
            )
            
            # NUEVOS DATOS
            data['distribucion_carga'] = db.execute_query(
                queries.get_distribucion_carga_profesionales(), params
            )
            data['productividad'] = db.execute_query(
                queries.get_productividad_profesionales(), params
            )
            data['por_servicio'] = db.execute_query(
                queries.get_atenciones_por_servicio(), params
            )
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return None
        
        return data
    
    data = load_profesionales_data(fecha_inicio, fecha_fin)
    
    if data is None:
        st.error("Error al cargar datos de profesionales")
        st.stop()
    
    # =======================================================================
    # MÉTRICAS PRINCIPALES
    # =======================================================================
    if not data['estadisticas'].empty:
        stats = data['estadisticas'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_metric_card(
                "📋",
                "TOTAL ATENCIONES",
                f"{int(stats.get('Total_Atenciones', 0)):,}",
                COLORS['primary'],
                COLORS['secondary']
            )
        
        with col2:
            render_metric_card(
                "👨‍⚕️",
                "PROFESIONALES ACTIVOS",
                f"{int(stats.get('Profesionales_Activos', 0)):,}",
                COLORS['success'],
                COLORS['info']
            )
        
        with col3:
            render_metric_card(
                "✅",
                "REALIZADAS",
                f"{int(stats.get('Atenciones_Realizadas', 0)):,}",
                COLORS['info'],
                COLORS['primary']
            )
        
        with col4:
            render_metric_card(
                "⏳",
                "PENDIENTES",
                f"{int(stats.get('Atenciones_Pendientes', 0)):,}",
                COLORS['warning'],
                COLORS['danger']
            )
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: DISTRIBUCIÓN DE CARGA
    # =======================================================================
    render_section_banner("⚖️", "Distribución de Carga de Trabajo (Top 15)")
    
    if not data['distribucion_carga'].empty:
        fig_carga = px.bar(
            data['distribucion_carga'],
            x='Total_Atenciones',
            y='Profesional',
            orientation='h',
            color='Porcentaje_Carga',
            color_continuous_scale='Blues',
            hover_data={'Porcentaje_Carga': ':.1f'}
        )
        
        fig_carga.update_layout(
            height=600,
            yaxis={'categoryorder':'total ascending'},
            xaxis_title="Total de Atenciones",
            yaxis_title="Profesional"
        )
        
        st.plotly_chart(fig_carga, use_container_width=True)
        
        # Análisis de carga
        promedio_atenciones = data['distribucion_carga']['Total_Atenciones'].mean()
        max_atenciones = data['distribucion_carga']['Total_Atenciones'].max()
        profesional_max = data['distribucion_carga'].loc[
            data['distribucion_carga']['Total_Atenciones'].idxmax()
        ]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Promedio por Profesional", f"{promedio_atenciones:.0f}")
        with col2:
            st.metric("Carga Máxima", f"{int(max_atenciones):,}")
        with col3:
            st.metric("Profesional con Mayor Carga", profesional_max['Profesional'])
        
        st.dataframe(
            data['distribucion_carga'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de distribución de carga")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: PRODUCTIVIDAD
    # =======================================================================
    render_section_banner("📊", "Productividad de Profesionales (Top 15)")
    
    if not data['productividad'].empty:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            fig_prod = go.Figure()
            
            fig_prod.add_trace(go.Bar(
                name='Realizadas',
                x=data['productividad']['Profesional'],
                y=data['productividad']['Realizadas'],
                marker_color=COLORS['success']
            ))
            
            fig_prod.add_trace(go.Bar(
                name='Pendientes',
                x=data['productividad']['Profesional'],
                y=data['productividad']['Pendientes'],
                marker_color=COLORS['warning']
            ))
            
            fig_prod.update_layout(
                barmode='stack',
                height=500,
                xaxis_title="Profesional",
                yaxis_title="Cantidad de Atenciones",
                xaxis={'tickangle': -45}
            )
            
            st.plotly_chart(fig_prod, use_container_width=True)
        
        with col2:
            st.markdown("### 🏆 Top 3 Cumplimiento")
            top_3 = data['productividad'].nlargest(3, 'Porcentaje_Cumplimiento')
            
            for idx, row in top_3.iterrows():
                st.metric(
                    label=row['Profesional'][:15] + '...' if len(row['Profesional']) > 15 else row['Profesional'],
                    value=f"{row['Porcentaje_Cumplimiento']:.1f}%",
                    delta=f"{int(row['Realizadas'])}/{int(row['Total_Atenciones'])}"
                )
        
        # Tabla completa
        st.dataframe(
            data['productividad'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de productividad")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: ATENCIONES POR SERVICIO
    # =======================================================================
    render_section_banner("🏥", "Distribución de Atenciones por Servicio")
    
    if not data['por_servicio'].empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_servicio = px.pie(
                data['por_servicio'],
                values='Total_Atenciones',
                names='Servicio',
                title="Top 10 Servicios",
                color_discrete_sequence=[
                    COLORS['primary'], COLORS['info'], COLORS['success'],
                    COLORS['warning'], COLORS['secondary'], COLORS['danger'],
                    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'
                ]
            )
            
            fig_servicio.update_traces(textposition='inside', textinfo='percent+label')
            fig_servicio.update_layout(height=500)
            st.plotly_chart(fig_servicio, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Top 5 Servicios")
            for idx, row in data['por_servicio'].head(5).iterrows():
                total = int(row['Total_Atenciones'])
                porcentaje = (total / data['por_servicio']['Total_Atenciones'].sum()) * 100
                st.metric(
                    label=row['Servicio'][:20] + '...' if len(row['Servicio']) > 20 else row['Servicio'],
                    value=f"{total:,}",
                    delta=f"{porcentaje:.1f}%"
                )
        
        st.dataframe(
            data['por_servicio'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos por servicio")
    
    render_section_divider()
    
    # =======================================================================
    # TOP PROFESIONALES (TABLA EXISTENTE)
    # =======================================================================
    render_section_banner("👥", "Ranking de Profesionales")
    
    if not data['top_profesionales'].empty:
        st.dataframe(
            data['top_profesionales'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de profesionales")
    
    # Footer
    render_footer()

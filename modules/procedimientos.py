"""
Módulo Procedimientos - Análisis Completo con Top y Horarios
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

def render_procedimientos():
    """Función principal del módulo de Procedimientos"""
    
    render_section_banner("🔬", "Análisis de Procedimientos")
    
    # Obtener filtros del sidebar
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    # Cargar datos
    @st.cache_data(ttl=CACHE_TTL)
    def load_procedimientos_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            
            data['estadisticas'] = db.execute_query(
                queries.get_estadisticas_procedimientos(), params
            )
            data['por_servicio'] = db.execute_query(
                queries.get_procedimientos_por_servicio(), params
            )
            
            # NUEVOS DATOS
            data['top_procedimientos'] = db.execute_query(
                queries.get_top_procedimientos(), params
            )
            data['por_turno'] = db.execute_query(
                queries.get_procedimientos_por_hora(), params
            )
            data['tendencia_semanal'] = db.execute_query(
                queries.get_tendencia_semanal_procedimientos()
            )
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return None
        
        return data
    
    data = load_procedimientos_data(fecha_inicio, fecha_fin)
    
    if data is None:
        st.error("Error al cargar datos de procedimientos")
        st.stop()
    
    # =======================================================================
    # MÉTRICAS PRINCIPALES
    # =======================================================================
    if not data['estadisticas'].empty:
        stats = data['estadisticas'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_metric_card(
                "🔬",
                "TOTAL PROCEDIMIENTOS",
                f"{int(stats.get('Total_Procedimientos', 0)):,}",
                COLORS['primary'],
                COLORS['secondary']
            )
        
        with col2:
            render_metric_card(
                "🏥",
                "SERVICIOS ACTIVOS",
                f"{int(stats.get('Servicios_Activos', 0)):,}",
                COLORS['info'],
                COLORS['primary']
            )
        
        with col3:
            render_metric_card(
                "👥",
                "PACIENTES",
                f"{int(stats.get('Pacientes_Atendidos', 0)):,}",
                COLORS['success'],
                COLORS['info']
            )
        
        with col4:
            promedio = stats.get('Promedio_Por_Dia', 0) or 0
            render_metric_card(
                "📊",
                "PROMEDIO/DÍA",
                f"{promedio:.1f}",
                COLORS['warning'],
                COLORS['danger']
            )
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: TOP 10 PROCEDIMIENTOS
    # =======================================================================
    render_section_banner("🏆", "Top 10 Procedimientos Más Realizados")
    
    if not data['top_procedimientos'].empty:
        # Truncar nombres largos para visualización
        top_10 = data['top_procedimientos'].copy()
        top_10['Nombre_Corto'] = top_10['Nombre'].apply(
            lambda x: x[:50] + '...' if len(str(x)) > 50 else x
        )
        
        fig_top = px.bar(
            top_10,
            x='Total',
            y='Nombre_Corto',
            orientation='h',
            color='Total',
            color_continuous_scale='Blues',
            hover_data={'Nombre': True, 'Codigo': True}
        )
        
        fig_top.update_layout(
            height=600,
            yaxis={'categoryorder':'total ascending'},
            xaxis_title="Cantidad Realizada",
            yaxis_title="Procedimiento",
            showlegend=False
        )
        
        st.plotly_chart(fig_top, use_container_width=True)
        
        # Tabla detallada
        st.dataframe(
            data['top_procedimientos'][['Codigo', 'Nombre', 'Total']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de top procedimientos")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: DISTRIBUCIÓN POR TURNO
    # =======================================================================
    render_section_banner("🕐", "Distribución por Turno del Día")
    
    if not data['por_turno'].empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_turno = px.bar(
                data['por_turno'],
                x='Turno',
                y='Total',
                color='Turno',
                color_discrete_map={
                    'Mañana (6am-2pm)': COLORS['warning'],
                    'Tarde (2pm-10pm)': COLORS['info'],
                    'Noche (10pm-6am)': COLORS['primary']
                }
            )
            
            fig_turno.update_layout(
                height=400,
                xaxis_title="Turno",
                yaxis_title="Cantidad de Procedimientos",
                showlegend=False
            )
            
            st.plotly_chart(fig_turno, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Resumen por Turno")
            for _, row in data['por_turno'].iterrows():
                total = int(row['Total'])
                porcentaje = (total / data['por_turno']['Total'].sum()) * 100
                st.metric(
                    label=row['Turno'],
                    value=f"{total:,}",
                    delta=f"{porcentaje:.1f}%"
                )
    else:
        st.info("No hay datos de distribución por turno")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: TENDENCIA SEMANAL
    # =======================================================================
    render_section_banner("📈", "Tendencia Semanal (Últimos 7 Días)")
    
    if not data['tendencia_semanal'].empty:
        fig_tendencia = go.Figure()
        
        fig_tendencia.add_trace(go.Scatter(
            x=data['tendencia_semanal']['Fecha'],
            y=data['tendencia_semanal']['Total_Procedimientos'],
            mode='lines+markers',
            name='Procedimientos',
            line=dict(color=COLORS['primary'], width=3),
            marker=dict(size=10),
            fill='tozeroy',
            fillcolor=f"rgba(44, 95, 45, 0.2)"
        ))
        
        fig_tendencia.update_layout(
            title="Evolución de Procedimientos",
            xaxis_title="Fecha",
            yaxis_title="Cantidad",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_tendencia, use_container_width=True)
        
        # Estadísticas de la semana
        col1, col2, col3 = st.columns(3)
        
        total_semana = data['tendencia_semanal']['Total_Procedimientos'].sum()
        promedio_dia = data['tendencia_semanal']['Total_Procedimientos'].mean()
        dia_max = data['tendencia_semanal'].loc[
            data['tendencia_semanal']['Total_Procedimientos'].idxmax()
        ]
        
        with col1:
            st.metric("Total Semana", f"{int(total_semana):,}")
        with col2:
            st.metric("Promedio Diario", f"{promedio_dia:.1f}")
        with col3:
            st.metric(
                "Día Máximo",
                f"{int(dia_max['Total_Procedimientos']):,}",
                delta=dia_max['Fecha'].strftime('%d/%m')
            )
    else:
        st.info("No hay datos de tendencia semanal")
    
    render_section_divider()
    
    # =======================================================================
    # PROCEDIMIENTOS POR SERVICIO
    # =======================================================================
    render_section_banner("🏥", "Distribución por Servicio")
    
    if not data['por_servicio'].empty:
        top_servicios = data['por_servicio'].head(10)
        
        fig_serv = px.pie(
            top_servicios,
            values='Total',
            names='Servicio',
            title="Top 10 Servicios",
            color_discrete_sequence=[
                COLORS['primary'], COLORS['info'], COLORS['success'],
                COLORS['warning'], COLORS['secondary'], COLORS['danger'],
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'
            ]
        )
        
        fig_serv.update_traces(textposition='inside', textinfo='percent+label')
        fig_serv.update_layout(height=500)
        st.plotly_chart(fig_serv, use_container_width=True)
    else:
        st.info("No hay datos por servicio")
    
    # Footer
    render_footer()

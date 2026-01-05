"""
Módulo Admisiones - Análisis Completo con Tendencias y Diagnósticos
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

def render_admisiones():
    """Función principal del módulo de Admisiones"""
    
    render_section_banner("🏥", "Análisis de Admisiones")
    
    # Obtener filtros del sidebar
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    # Cargar datos
    @st.cache_data(ttl=CACHE_TTL)
    def load_admisiones_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            # Datos existentes
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            data['estadisticas'] = db.execute_query(
                queries.get_estadisticas_admisiones(), params
            )
            data['distribucion'] = db.execute_query(
                queries.get_distribucion_tipo_atencion(), params
            )
            data['por_servicio'] = db.execute_query(
                queries.get_admisiones_por_servicio(), params
            )
            
            # NUEVOS DATOS
            data['tendencia_semanal'] = db.execute_query(
                queries.get_tendencia_semanal_admisiones()
            )
            data['top_diagnosticos'] = db.execute_query(
                queries.get_top_diagnosticos_ingreso()
            )
            data['tiempos_estancia'] = db.execute_query(
                queries.get_tiempos_estancia()
            )
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return None
        
        return data
    
    data = load_admisiones_data(fecha_inicio, fecha_fin)
    
    if data is None:
        st.error("Error al cargar datos de admisiones")
        st.stop()
    
    # =======================================================================
    # MÉTRICAS PRINCIPALES
    # =======================================================================
    if not data['estadisticas'].empty:
        stats = data['estadisticas'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_metric_card(
                "📊",
                "TOTAL ADMISIONES",
                f"{int(stats.get('Total_Admisiones', 0)):,}",
                COLORS['primary'],
                COLORS['secondary']
            )
        
        with col2:
            render_metric_card(
                "✅",
                "ACTIVAS",
                f"{int(stats.get('Activas', 0)):,}",
                COLORS['success'],
                COLORS['info']
            )
        
        with col3:
            render_metric_card(
                "🚨",
                "URGENCIAS",
                f"{int(stats.get('Urgencias', 0)):,}",
                COLORS['warning'],
                COLORS['danger']
            )
        
        with col4:
            render_metric_card(
                "🛏️",
                "HOSPITALIZACIÓN",
                f"{int(stats.get('Hospitalizacion', 0)):,}",
                COLORS['info'],
                COLORS['primary']
            )
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: TENDENCIA SEMANAL
    # =======================================================================
    render_section_banner("📈", "Tendencia Semanal (Últimos 7 Días)")
    
    if not data['tendencia_semanal'].empty:
        fig_tendencia = go.Figure()
        
        fig_tendencia.add_trace(go.Scatter(
            x=data['tendencia_semanal']['Fecha'],
            y=data['tendencia_semanal']['Total_Admisiones'],
            mode='lines+markers',
            name='Total',
            line=dict(color=COLORS['primary'], width=3),
            marker=dict(size=10)
        ))
        
        fig_tendencia.add_trace(go.Scatter(
            x=data['tendencia_semanal']['Fecha'],
            y=data['tendencia_semanal']['Urgencias'],
            mode='lines+markers',
            name='Urgencias',
            line=dict(color=COLORS['warning'], width=2),
            marker=dict(size=8)
        ))
        
        fig_tendencia.add_trace(go.Scatter(
            x=data['tendencia_semanal']['Fecha'],
            y=data['tendencia_semanal']['Hospitalizacion'],
            mode='lines+markers',
            name='Hospitalización',
            line=dict(color=COLORS['info'], width=2),
            marker=dict(size=8)
        ))
        
        fig_tendencia.update_layout(
            title="Evolución de Admisiones",
            xaxis_title="Fecha",
            yaxis_title="Cantidad",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_tendencia, use_container_width=True)
    else:
        st.info("No hay datos de tendencia semanal")
    
    render_section_divider()
    
    # =======================================================================
    # DISTRIBUCIÓN POR TIPO DE ATENCIÓN
    # =======================================================================
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        render_section_banner("📊", "Distribución por Tipo")
        
        if not data['distribucion'].empty:
            fig_dist = px.pie(
                data['distribucion'],
                values='Total',
                names='Tipo_Atencion',
                color_discrete_sequence=[COLORS['primary'], COLORS['warning'], COLORS['info'], COLORS['secondary']]
            )
            fig_dist.update_traces(textposition='inside', textinfo='percent+label')
            fig_dist.update_layout(height=400)
            st.plotly_chart(fig_dist, use_container_width=True)
    
    with col_der:
        render_section_banner("🏥", "Por Servicio (Top 10)")
        
        if not data['por_servicio'].empty:
            top_servicios = data['por_servicio'].head(10)
            fig_serv = px.bar(
                top_servicios,
                x='Total_Admisiones',
                y='Servicio',
                orientation='h',
                color_discrete_sequence=[COLORS['primary']]
            )
            fig_serv.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_serv, use_container_width=True)
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: TOP DIAGNÓSTICOS DE INGRESO
    # =======================================================================
    render_section_banner("🔬", "Top 10 Diagnósticos de Ingreso (Últimos 30 Días)")
    
    if not data['top_diagnosticos'].empty:
        fig_diag = px.bar(
            data['top_diagnosticos'],
            x='Total',
            y='Codigo',
            orientation='h',
            title="Diagnósticos CIE-10 Más Frecuentes",
            color_discrete_sequence=[COLORS['info']]
        )
        fig_diag.update_layout(
            height=500,
            yaxis={'categoryorder':'total ascending'},
            xaxis_title="Cantidad de Casos",
            yaxis_title="Código CIE-10"
        )
        st.plotly_chart(fig_diag, use_container_width=True)
        
        # Tabla detallada
        st.dataframe(
            data['top_diagnosticos'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de diagnósticos de ingreso")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: TIEMPOS DE ESTANCIA
    # =======================================================================
    render_section_banner("⏱️", "Tiempos de Estancia - Hospitalización")
    
    if not data['tiempos_estancia'].empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_estancia = px.pie(
                data['tiempos_estancia'],
                values='Total',
                names='Rango',
                title="Distribución de Tiempos de Estancia",
                color_discrete_sequence=[COLORS['success'], COLORS['warning'], COLORS['danger']]
            )
            fig_estancia.update_traces(textposition='inside', textinfo='percent+label+value')
            fig_estancia.update_layout(height=400)
            st.plotly_chart(fig_estancia, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Resumen")
            for _, row in data['tiempos_estancia'].iterrows():
                st.metric(
                    label=row['Rango'],
                    value=f"{int(row['Total']):,} casos"
                )
    else:
        st.info("No hay datos de tiempos de estancia")
    
    # Footer
    render_footer()

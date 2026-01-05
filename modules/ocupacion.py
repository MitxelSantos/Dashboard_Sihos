"""
Módulo Ocupación - Análisis Completo con Histórico, Rotación y Distribución
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
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

def render_ocupacion():
    """Función principal del módulo de Ocupación"""
    
    render_section_banner("🛏️", "Ocupación de Camas en Tiempo Real")
    
    # Cargar datos
    @st.cache_data(ttl=300)  # Cache de 5 minutos para datos en tiempo real
    def load_ocupacion_data():
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            data['general'] = db.execute_query(queries.get_ocupacion_general())
            data['por_servicio'] = db.execute_query(queries.get_ocupacion_por_servicio())
            
            # NUEVOS DATOS
            data['historico'] = db.execute_query(queries.get_historico_ocupacion())
            data['rotacion'] = db.execute_query(queries.get_rotacion_camas())
            data['distribucion_tipo'] = db.execute_query(queries.get_distribucion_tipo_cama())
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return None
        
        return data
    
    data = load_ocupacion_data()
    
    if data is None:
        st.error("Error al cargar datos de ocupación")
        st.stop()
    
    # =======================================================================
    # MÉTRICAS PRINCIPALES
    # =======================================================================
    if not data['general'].empty:
        general = data['general'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        porcentaje = general.get('Porcentaje_Ocupacion', 0) or 0
        color_principal = (COLORS['danger'] if porcentaje > 80 
                          else COLORS['warning'] if porcentaje > 60 
                          else COLORS['success'])
        
        with col1:
            render_metric_card(
                "🏥",
                "TOTAL CAMAS",
                f"{int(general.get('Total_Camas', 0)):,}",
                COLORS['primary'],
                COLORS['secondary']
            )
        
        with col2:
            render_metric_card(
                "✅",
                "OCUPADAS",
                f"{int(general.get('Ocupadas', 0)):,}",
                color_principal,
                COLORS['info']
            )
        
        with col3:
            render_metric_card(
                "🆓",
                "LIBRES",
                f"{int(general.get('Libres', 0)):,}",
                COLORS['success'],
                COLORS['secondary']
            )
        
        with col4:
            render_metric_card(
                "📊",
                "% OCUPACIÓN",
                f"{porcentaje:.1f}%",
                color_principal,
                COLORS['danger']
            )
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: HISTÓRICO 7 DÍAS
    # =======================================================================
    render_section_banner("📈", "Histórico de Ocupación (Últimos 7 Días)")
    
    if not data['historico'].empty:
        fig_historico = go.Figure()
        
        # Línea de ocupación
        fig_historico.add_trace(go.Scatter(
            x=data['historico']['Fecha'],
            y=data['historico']['Porcentaje_Ocupacion'],
            mode='lines+markers',
            name='% Ocupación',
            line=dict(color=COLORS['primary'], width=3),
            marker=dict(size=10),
            fill='tozeroy',
            fillcolor=f"rgba(44, 95, 45, 0.2)"
        ))
        
        # Líneas de referencia
        fig_historico.add_hline(y=90, line_dash="dash", line_color="red", 
                                annotation_text="Crítico (90%)")
        fig_historico.add_hline(y=70, line_dash="dash", line_color="orange",
                                annotation_text="Alerta (70%)")
        
        fig_historico.update_layout(
            title="Evolución del Porcentaje de Ocupación",
            xaxis_title="Fecha",
            yaxis_title="% Ocupación",
            hovermode='x unified',
            height=450,
            yaxis_range=[0, 100]
        )
        
        st.plotly_chart(fig_historico, use_container_width=True)
        
        # Tabla de datos
        st.dataframe(
            data['historico'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos históricos disponibles")
    
    render_section_divider()
    
    # =======================================================================
    # OCUPACIÓN POR SERVICIO
    # =======================================================================
    render_section_banner("🏥", "Ocupación por Servicio")
    
    if not data['por_servicio'].empty:
        # Agregar columna de color según porcentaje
        def get_color_estado(porcentaje):
            if porcentaje >= 90:
                return '🔴 CRÍTICO'
            elif porcentaje >= 70:
                return '🟡 ALERTA'
            else:
                return '🟢 NORMAL'
        
        data['por_servicio']['Estado'] = data['por_servicio']['Porcentaje_Ocupacion'].apply(get_color_estado)
        
        fig_servicio = px.bar(
            data['por_servicio'].head(15),
            x='Porcentaje_Ocupacion',
            y='Servicio',
            orientation='h',
            color='Porcentaje_Ocupacion',
            color_continuous_scale='RdYlGn_r',
            range_color=[0, 100]
        )
        
        fig_servicio.update_layout(
            height=600,
            yaxis={'categoryorder':'total ascending'},
            xaxis_title="% Ocupación",
            yaxis_title="Servicio"
        )
        
        st.plotly_chart(fig_servicio, use_container_width=True)
        
        st.dataframe(
            data['por_servicio'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos por servicio")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: ROTACIÓN DE CAMAS
    # =======================================================================
    render_section_banner("🔄", "Rotación de Camas (Últimos 30 Días)")
    
    if not data['rotacion'].empty:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            fig_rotacion = px.scatter(
                data['rotacion'],
                x='Promedio_Dias_Ocupada',
                y='Veces_Usada',
                size='Veces_Usada',
                hover_data=['CodiCama', 'NombCama'],
                color='Veces_Usada',
                color_continuous_scale='Viridis',
                title="Rotación: Uso vs Días Ocupada"
            )
            
            fig_rotacion.update_layout(
                height=500,
                xaxis_title="Promedio de Días Ocupada",
                yaxis_title="Veces Usada"
            )
            
            st.plotly_chart(fig_rotacion, use_container_width=True)
        
        with col2:
            st.markdown("### 🏆 Top 5 Más Usadas")
            for idx, row in data['rotacion'].head(5).iterrows():
                st.metric(
                    label=row['NombCama'],
                    value=f"{int(row['Veces_Usada'])} veces",
                    delta=f"{row['Promedio_Dias_Ocupada']:.1f} días"
                )
        
        # Tabla completa
        st.dataframe(
            data['rotacion'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de rotación de camas")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: DISTRIBUCIÓN POR TIPO DE CAMA
    # =======================================================================
    render_section_banner("📊", "Distribución por Tipo de Cama")
    
    if not data['distribucion_tipo'].empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig_tipo_total = px.pie(
                data['distribucion_tipo'],
                values='Total',
                names='Tipo',
                title="Distribución Total",
                color_discrete_sequence=[COLORS['primary'], COLORS['info'], COLORS['success']]
            )
            fig_tipo_total.update_traces(textposition='inside', textinfo='percent+label+value')
            st.plotly_chart(fig_tipo_total, use_container_width=True)
        
        with col2:
            fig_tipo_ocup = px.bar(
                data['distribucion_tipo'],
                x='Tipo',
                y=['Total', 'Ocupadas'],
                barmode='group',
                color_discrete_sequence=[COLORS['secondary'], COLORS['danger']]
            )
            fig_tipo_ocup.update_layout(
                title="Total vs Ocupadas por Tipo",
                xaxis_title="Tipo de Cama",
                yaxis_title="Cantidad"
            )
            st.plotly_chart(fig_tipo_ocup, use_container_width=True)
        
        # Tabla resumen
        st.dataframe(
            data['distribucion_tipo'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de distribución por tipo")
    
    # Footer
    render_footer()

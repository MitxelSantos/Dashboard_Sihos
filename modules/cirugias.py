"""
Módulo Cirugías - Análisis Completo con Anestesia, Horarios y Día
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

def render_cirugias():
    """Función principal del módulo de Cirugías"""
    
    render_section_banner("⚕️", "Análisis de Cirugías")
    
    # Obtener filtros del sidebar
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    # Cargar datos
    @st.cache_data(ttl=CACHE_TTL)
    def load_cirugias_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            
            data['estadisticas'] = db.execute_query(
                queries.get_estadisticas_cirugias(), params
            )
            data['por_anestesia'] = db.execute_query(
                queries.get_distribucion_anestesia(), params
            )
            
            # NUEVOS DATOS
            data['duracion_anestesia'] = db.execute_query(
                queries.get_duracion_por_anestesia(), params
            )
            data['por_hora'] = db.execute_query(
                queries.get_cirugias_por_hora(), params
            )
            data['por_dia_semana'] = db.execute_query(
                queries.get_cirugias_por_dia_semana(), params
            )
            data['top_procedimientos'] = db.execute_query(
                queries.get_top_procedimientos_quirurgicos(), params
            )
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return None
        
        return data
    
    data = load_cirugias_data(fecha_inicio, fecha_fin)
    
    if data is None:
        st.error("Error al cargar datos de cirugías")
        st.stop()
    
    # =======================================================================
    # MÉTRICAS PRINCIPALES
    # =======================================================================
    if not data['estadisticas'].empty:
        stats = data['estadisticas'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_metric_card(
                "⚕️",
                "TOTAL CIRUGÍAS",
                f"{int(stats.get('Total_Cirugias', 0)):,}",
                COLORS['danger'],
                COLORS['warning']
            )
        
        with col2:
            duracion = stats.get('Duracion_Promedio', 0) or 0
            render_metric_card(
                "⏱️",
                "DURACIÓN PROMEDIO",
                f"{int(duracion)} min",
                COLORS['warning'],
                COLORS['info']
            )
        
        with col3:
            render_metric_card(
                "📊",
                "ANESTESIA GENERAL",
                f"{int(stats.get('Anestesia_General', 0)):,}",
                COLORS['primary'],
                COLORS['secondary']
            )
        
        with col4:
            render_metric_card(
                "💉",
                "ANESTESIA REGIONAL",
                f"{int(stats.get('Anestesia_Regional', 0)):,}",
                COLORS['info'],
                COLORS['success']
            )
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: DURACIÓN POR TIPO DE ANESTESIA
    # =======================================================================
    render_section_banner("⏱️", "Duración Promedio por Tipo de Anestesia")
    
    if not data['duracion_anestesia'].empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_duracion = px.bar(
                data['duracion_anestesia'],
                x='Tipo_Anestesia',
                y='Promedio_Minutos',
                color='Tipo_Anestesia',
                text='Promedio_Minutos',
                color_discrete_map={
                    'General': COLORS['danger'],
                    'Regional': COLORS['warning'],
                    'Local': COLORS['info']
                }
            )
            
            fig_duracion.update_traces(texttemplate='%{text:.0f} min', textposition='outside')
            fig_duracion.update_layout(
                height=400,
                xaxis_title="Tipo de Anestesia",
                yaxis_title="Duración Promedio (minutos)",
                showlegend=False
            )
            
            st.plotly_chart(fig_duracion, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Resumen")
            for _, row in data['duracion_anestesia'].iterrows():
                st.metric(
                    label=row['Tipo_Anestesia'],
                    value=f"{int(row['Promedio_Minutos'])} min",
                    delta=f"{int(row['Total_Cirugias'])} cirugías"
                )
    else:
        st.info("No hay datos de duración por anestesia")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: HORARIOS DE CIRUGÍAS (0-23)
    # =======================================================================
    render_section_banner("🕐", "Distribución por Hora del Día")
    
    if not data['por_hora'].empty:
        fig_hora = px.bar(
            data['por_hora'],
            x='Hora',
            y='Total',
            color='Total',
            color_continuous_scale='Reds'
        )
        
        fig_hora.update_layout(
            height=450,
            xaxis_title="Hora del Día",
            yaxis_title="Cantidad de Cirugías",
            xaxis=dict(
                tickmode='linear',
                dtick=1
            ),
            showlegend=False
        )
        
        st.plotly_chart(fig_hora, use_container_width=True)
        
        # Estadísticas horarias
        hora_max = data['por_hora'].loc[data['por_hora']['Total'].idxmax()]
        total_mañana = data['por_hora'][
            (data['por_hora']['Hora'] >= 6) & (data['por_hora']['Hora'] < 12)
        ]['Total'].sum()
        total_tarde = data['por_hora'][
            (data['por_hora']['Hora'] >= 12) & (data['por_hora']['Hora'] < 18)
        ]['Total'].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Hora Pico", f"{int(hora_max['Hora'])}:00 hrs", f"{int(hora_max['Total'])} cirugías")
        with col2:
            st.metric("Mañana (6am-12pm)", f"{int(total_mañana)}")
        with col3:
            st.metric("Tarde (12pm-6pm)", f"{int(total_tarde)}")
    else:
        st.info("No hay datos de distribución por hora")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: CIRUGÍAS POR DÍA DE LA SEMANA
    # =======================================================================
    render_section_banner("📅", "Distribución por Día de la Semana")
    
    if not data['por_dia_semana'].empty:
        fig_dia = px.bar(
            data['por_dia_semana'],
            x='Dia_Semana',
            y='Total',
            color='Total',
            color_continuous_scale='Greens'
        )
        
        fig_dia.update_layout(
            height=400,
            xaxis_title="Día de la Semana",
            yaxis_title="Cantidad de Cirugías",
            showlegend=False,
            xaxis={'categoryorder':'array', 'categoryarray':['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']}
        )
        
        st.plotly_chart(fig_dia, use_container_width=True)
        
        # Tabla resumen
        st.dataframe(
            data['por_dia_semana'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos por día de la semana")
    
    render_section_divider()
    
    # =======================================================================
    # NUEVA SECCIÓN: TOP PROCEDIMIENTOS QUIRÚRGICOS
    # =======================================================================
    render_section_banner("🏆", "Top 10 Diagnósticos Post-Operatorios")
    
    if not data['top_procedimientos'].empty:
        fig_top = px.bar(
            data['top_procedimientos'],
            x='Total',
            y='Codigo',
            orientation='h',
            color='Total',
            color_continuous_scale='Purples'
        )
        
        fig_top.update_layout(
            height=500,
            yaxis={'categoryorder':'total ascending'},
            xaxis_title="Cantidad de Cirugías",
            yaxis_title="Código Diagnóstico",
            showlegend=False
        )
        
        st.plotly_chart(fig_top, use_container_width=True)
        
        st.dataframe(
            data['top_procedimientos'],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay datos de procedimientos quirúrgicos")
    
    # Footer
    render_footer()

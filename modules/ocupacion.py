"""
Módulo Ocupación - Análisis Completo en Tiempo Real
5 opciones distribución, 5 métricas tendencias
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

def render_ocupacion():
    """Función principal del módulo de Ocupación"""
    
    render_section_banner("🛏️", "Ocupación de Camas en Tiempo Real")
    
    @st.cache_data(ttl=300)  # Cache de 5 minutos
    def load_ocupacion_data():
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            data['general'] = db.execute_query(queries.get_ocupacion_general())
            data['por_servicio'] = db.execute_query(queries.get_ocupacion_por_servicio())
            data['historico'] = db.execute_query(queries.get_historico_ocupacion())
            data['rotacion'] = db.execute_query(queries.get_rotacion_camas())
            data['distribucion_tipo'] = db.execute_query(queries.get_distribucion_tipo_cama())
            data['por_uci'] = db.execute_query(queries.get_ocupacion_por_uci())
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return None
        
        return data
    
    data = load_ocupacion_data()
    
    if data is None:
        st.error("Error al cargar datos de ocupación")
        st.stop()
    
    # MÉTRICAS
    if not data['general'].empty:
        general = data['general'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        porcentaje = general.get('Porcentaje_Ocupacion', 0) or 0
        color_principal = COLORS['danger'] if porcentaje > 80 else COLORS['warning'] if porcentaje > 60 else COLORS['success']
        
        with col1:
            render_metric_card("🏥", "TOTAL CAMAS", f"{int(general.get('Total_Camas', 0)):,}", COLORS['primary'], COLORS['secondary'])
        
        with col2:
            render_metric_card("✅", "OCUPADAS", f"{int(general.get('Ocupadas', 0)):,}", color_principal, COLORS['info'])
        
        with col3:
            render_metric_card("🆓", "LIBRES", f"{int(general.get('Libres', 0)):,}", COLORS['success'], COLORS['secondary'])
        
        with col4:
            render_metric_card("📊", "% OCUPACIÓN", f"{porcentaje:.1f}%", color_principal, COLORS['danger'])
    
    render_section_divider()
    
    # DISTRIBUCIÓN
    render_section_banner("📊", "Distribución de Ocupación")
    
    col_dist, col_grafica = st.columns([2, 2])
    
    with col_dist:
        opcion_dist = st.radio(
            "Ver distribución por:",
            ["Por Servicio", "Por Tipo de Cama", "UCI vs No-UCI", "Rotación de Camas", "Estado Crítico"],
            horizontal=True,
            key="radio_dist_ocup"
        )
    
    with col_grafica:
        tipo_grafica_dist = st.radio(
            "Tipo de gráfica:",
            ["🥧 Pie Chart", "📊 Bar Horizontal", "📊 Bar Agrupadas", "☀️ Sunburst", "🌳 Treemap"],
            horizontal=True,
            key="radio_tipo_grafica_dist_ocup"
        )
    
    datos_dict = {
        "Por Servicio": (data['por_servicio'], 'Servicio', 'Porcentaje_Ocupacion'),
        "Por Tipo de Cama": (data['distribucion_tipo'], 'Tipo', 'Ocupadas'),
        "UCI vs No-UCI": (data['por_uci'], 'Tipo', 'Porcentaje_Ocupacion'),
        "Rotación de Camas": (data['rotacion'], 'NombCama', 'Veces_Usada'),
        "Estado Crítico": (data['por_servicio'].head(10), 'Servicio', 'Porcentaje_Ocupacion')
    }
    
    datos_dist, campo_nombre, campo_valor = datos_dict[opcion_dist]
    titulo = f"Distribución {opcion_dist}"
    
    if not datos_dist.empty:
        col_graf, col_metricas = st.columns([3, 1])
        
        with col_graf:
            fig_dist = None
            
            if "Pie" in tipo_grafica_dist:
                fig_dist = px.pie(datos_dist, values=campo_valor, names=campo_nombre, title=titulo)
            elif "Bar Horizontal" in tipo_grafica_dist:
                fig_dist = px.bar(datos_dist, x=campo_valor, y=campo_nombre, orientation='h', title=titulo, color_continuous_scale='RdYlGn_r' if 'Porcentaje' in campo_valor else 'Blues')
                fig_dist.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            elif "Bar Agrupadas" in tipo_grafica_dist:
                fig_dist = px.bar(datos_dist, x=campo_nombre, y=campo_valor, title=titulo)
                fig_dist.update_layout(showlegend=False)
            elif "Sunburst" in tipo_grafica_dist:
                df_s = datos_dist.copy()
                df_s['Root'] = 'Total'
                fig_dist = px.sunburst(df_s, path=['Root', campo_nombre], values=campo_valor, title=titulo)
            elif "Treemap" in tipo_grafica_dist:
                fig_dist = px.treemap(datos_dist, path=[campo_nombre], values=campo_valor, title=titulo)
            
            if fig_dist:
                fig_dist.update_layout(height=450)
                st.plotly_chart(fig_dist, use_container_width=True)
        
        with col_metricas:
            st.markdown("### 📊 Resumen")
            
            if 'Porcentaje' in campo_valor:
                promedio = datos_dist[campo_valor].mean()
                st.metric("Ocupación Promedio", f"{promedio:.1f}%")
            else:
                total = datos_dist[campo_valor].sum()
                st.metric("Total", f"{int(total):,}")
            
            top_3 = datos_dist.nlargest(3, campo_valor)
            st.markdown("#### 🏆 Top 3")
            for idx, row in top_3.iterrows():
                st.metric(label=str(row[campo_nombre])[:25], value=f"{row[campo_valor]:.1f}{'%' if 'Porcentaje' in campo_valor else ''}")
        
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(datos_dist, use_container_width=True, hide_index=True)
    else:
        st.info(f"No hay datos para {opcion_dist}")
    
    render_section_divider()
    
    # TENDENCIAS

    render_section_banner("📈", "Histórico de Ocupación (Ultimos 7 días)")
    
    if not data['historico'].empty:
        fig_historico = go.Figure()
        
        fig_historico.add_trace(go.Scatter(
            x=data['historico']['Fecha'],
            y=data['historico']['Porcentaje_Ocupacion'],
            mode='lines+markers',
            name='% Ocupación',
            line=dict(color=COLORS['primary'], width=3),
            marker=dict(size=10),
            fill='tozeroy'
        ))
        
        fig_historico.add_hline(y=90, line_dash="dash", line_color="red", annotation_text="Crítico (90%)")
        fig_historico.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Alerta (70%)")
        
        fig_historico.update_layout(
            title="Evolución del Porcentaje de Ocupación",
            xaxis_title="Fecha",
            yaxis_title="% Ocupación",
            hovermode='x unified',
            height=450,
            yaxis_range=[0, 100]
        )
        
        st.plotly_chart(fig_historico, use_container_width=True)
        
        st.markdown("### 📊 Resumen del Período")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            promedio = data['historico']['Porcentaje_Ocupacion'].mean()
            st.metric("Ocupación Promedio", f"{promedio:.1f}%")
        
        with col2:
            maximo = data['historico']['Porcentaje_Ocupacion'].max()
            st.metric("Ocupación Máxima", f"{maximo:.1f}%")
        
        with col3:
            minimo = data['historico']['Porcentaje_Ocupacion'].min()
            st.metric("Ocupación Mínima", f"{minimo:.1f}%")
        
        with col4:
            camas_prom = data['historico']['Camas_Ocupadas'].mean()
            st.metric("Camas Ocupadas Prom.", f"{camas_prom:.0f}")
    
    render_footer()

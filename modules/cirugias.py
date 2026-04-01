"""
Módulo Cirugías - Análisis Completo
7 opciones distribución, 6 métricas tendencias
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

def render_cirugias():
    """Función principal del módulo de Cirugías"""

    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)
    
    render_section_banner("⚕️", "Análisis de Cirugías", rango_fechas)
    
    @st.cache_data(ttl=CACHE_TTL)
    def load_cirugias_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            
            data['estadisticas'] = db.execute_query(queries.get_estadisticas_cirugias(), params)
            data['por_anestesia'] = db.execute_query(queries.get_distribucion_anestesia(), params)
            data['duracion_anestesia'] = db.execute_query(queries.get_duracion_por_anestesia(), params)
            data['por_hora'] = db.execute_query(queries.get_cirugias_por_hora(), params)
            data['por_dia_semana'] = db.execute_query(queries.get_cirugias_por_dia_semana(), params)
            data['por_duracion'] = db.execute_query(queries.get_cirugias_por_duracion(), params)
            data['top_procedimientos'] = db.execute_query(queries.get_top_procedimientos_quirurgicos(), params)
            
            # Tendencias
            query_tendencias = f"""
            SELECT 
                DATE(FechInic) as Fecha,
                COUNT(*) as Total_Cirugias,
                ROUND(AVG(TIMESTAMPDIFF(MINUTE, HoraInic, HoraFina)), 0) as Duracion_Promedio,
                COUNT(CASE WHEN TipoAnes = 1 THEN 1 END) as Anestesia_General,
                COUNT(CASE WHEN TipoAnes = 2 THEN 1 END) as Anestesia_Regional,
                COUNT(CASE WHEN TipoAnes = 3 THEN 1 END) as Anestesia_Local
            FROM ActoQuir
            WHERE FechInic BETWEEN '{f_inicio}' AND '{f_fin}'
            GROUP BY DATE(FechInic)
            ORDER BY Fecha
            """
            data['tendencias'] = db.execute_query(query_tendencias)

            data['analisis_duracion'] = db.execute_query(queries.get_analisis_duracion_cirugias(), params)
            data['dist_duracion'] = db.execute_query(queries.get_distribucion_duracion(), params)
            
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return None
        
        return data
    
    data = load_cirugias_data(fecha_inicio, fecha_fin)
    
    if data is None:
        st.error("Error al cargar datos de cirugías")
        st.stop()
    
    # MÉTRICAS
    if not data['estadisticas'].empty:
        stats = data['estadisticas'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_metric_card("⚕️", "TOTAL CIRUGÍAS", f"{int(stats.get('Total_Cirugias', 0)):,}", COLORS['danger'], COLORS['warning'])
        
        with col2:
            duracion = stats.get('Duracion_Promedio', 0) or 0
            render_metric_card("⏱️", "DURACIÓN PROMEDIO", f"{int(duracion)} min", COLORS['warning'], COLORS['info'])
        
        with col3:
            render_metric_card("📊", "ANESTESIA GENERAL", f"{int(stats.get('Anestesia_General', 0)):,}", COLORS['primary'], COLORS['secondary'])
        
        with col4:
            render_metric_card("💉", "ANESTESIA REGIONAL", f"{int(stats.get('Anestesia_Regional', 0)):,}", COLORS['info'], COLORS['success'])
    
    render_section_divider()
    
    # DISTRIBUCIÓN
    render_section_banner("📊", "Distribución de Cirugías", rango_fechas)
    
    col_dist, col_grafica = st.columns([2, 2])
    
    with col_dist:
        opcion_dist = st.radio(
            "Ver distribución por:",
            ["Tipo de Anestesia", "Día de Semana", "Rango de Duración", "Por Hora", "Top Diagnósticos"],
            horizontal=True,
            key="radio_dist_cirug"
        )
    
    with col_grafica:
        tipo_grafica_dist = st.radio(
            "Tipo de gráfica:",
            ["🥧 Pie Chart", "📊 Bar Horizontal", "📊 Bar Agrupadas", "☀️ Sunburst", "🌳 Treemap", "🗺️ Funnel"],
            horizontal=True,
            key="radio_tipo_grafica_dist_cirug"
        )
    
    datos_dict = {
        "Tipo de Anestesia": (data['por_anestesia'], 'Tipo_Anestesia', 'Total'),
        "Día de Semana": (data['por_dia_semana'], 'Dia_Semana', 'Total'),
        "Rango de Duración": (data['por_duracion'], 'Rango_Duracion', 'Total'),
        "Por Hora": (data['por_hora'], 'Hora', 'Total'),
        "Top Diagnósticos": (data['top_procedimientos'], 'Codigo', 'Total')
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
                fig_dist = px.bar(datos_dist, x=campo_valor, y=campo_nombre, orientation='h', title=titulo, color_continuous_scale='Blues')
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
            elif "Funnel" in tipo_grafica_dist:
                df_f = datos_dist.sort_values(campo_valor, ascending=False)
                fig_dist = px.funnel(df_f, x=campo_valor, y=campo_nombre, title=titulo)
            
            if fig_dist:
                fig_dist.update_layout(height=450)
                st.plotly_chart(fig_dist, use_container_width=True)
        
        with col_metricas:
            st.markdown("### 📊 Resumen")
            total = datos_dist[campo_valor].sum()
            st.metric("Total", f"{int(total):,}")
            
            top_3 = datos_dist.nlargest(3, campo_valor)
            st.markdown("#### 🏆 Top 3")
            for idx, row in top_3.iterrows():
                porcentaje = (row[campo_valor] / total) * 100
                st.metric(label=str(row[campo_nombre])[:25], value=f"{int(row[campo_valor]):,}", delta=f"{porcentaje:.1f}%")
        
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(datos_dist, use_container_width=True, hide_index=True)
            csv = datos_dist.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(label="📥 Descargar CSV", data=csv, file_name=f"cirugias_{opcion_dist.lower().replace(' ', '_')}_{fecha_inicio}_{fecha_fin}.csv", mime="text/csv")
    else:
        st.info(f"No hay datos para {opcion_dist}")
    
    render_section_divider()
    
    # TENDENCIAS
    render_section_banner("📈", "Tendencias en el Tiempo", rango_fechas)
    
    if not data['tendencias'].empty:
        col_metrica, col_tipo = st.columns([2, 2])
        
        with col_metrica:
            metrica_tendencia = st.radio(
                "Métrica a visualizar:",
                ["Total de Cirugías", "Duración Promedio", "Por Tipo de Anestesia"],
                horizontal=True,
                key="radio_metrica_tendencia_cirug"
            )
        
        with col_tipo:
            tipo_grafica = st.radio(
                "Tipo de gráfica:",
                ["📈 Línea", "📊 Barras", "📉 Área", "📊 Barras Apiladas", "📈 Área Apilada"],
                horizontal=True,
                key="radio_tipo_grafica_cirug"
            )
        
        fig_tendencia = None
        
        if metrica_tendencia in ["Por Tipo de Anestesia"]:
            if "Apiladas" in tipo_grafica or "Apilada" in tipo_grafica:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Bar(x=data['tendencias']['Fecha'], y=data['tendencias']['Anestesia_General'], name='General', marker_color=COLORS['danger']))
                fig_tendencia.add_trace(go.Bar(x=data['tendencias']['Fecha'], y=data['tendencias']['Anestesia_Regional'], name='Regional', marker_color=COLORS['warning']))
                fig_tendencia.add_trace(go.Bar(x=data['tendencias']['Fecha'], y=data['tendencias']['Anestesia_Local'], name='Local', marker_color=COLORS['info']))
            if "Área" in tipo_grafica and ("Apilada" in tipo_grafica or "Apiladas" in tipo_grafica):
                # Área Apilada - crear como Scatter desde inicio
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Anestesia_General'],
                    name='General',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['danger'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Anestesia_Regional'],
                    name='Regional',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['warning'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Anestesia_Local'],
                    name='Local',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['info'])
                ))
                fig_tendencia.update_layout(title="Cirugías por Tipo de Anestesia", height=450)
            else:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(x=data['tendencias']['Fecha'], y=data['tendencias']['Anestesia_General'], mode='lines+markers', name='General', line=dict(color=COLORS['danger'], width=2)))
                fig_tendencia.add_trace(go.Scatter(x=data['tendencias']['Fecha'], y=data['tendencias']['Anestesia_Regional'], mode='lines+markers', name='Regional', line=dict(color=COLORS['warning'], width=2)))
                fig_tendencia.add_trace(go.Scatter(x=data['tendencias']['Fecha'], y=data['tendencias']['Anestesia_Local'], mode='lines+markers', name='Local', line=dict(color=COLORS['info'], width=2)))
                fig_tendencia.update_layout(title="Cirugías por Tipo de Anestesia", height=450, hovermode='x unified')
        else:
            campo_y = 'Total_Cirugias' if metrica_tendencia == "Total de Cirugías" else 'Duracion_Promedio'
            titulo = metrica_tendencia
            color = COLORS['danger'] if metrica_tendencia == "Total de Cirugías" else COLORS['warning']
            
            if "Línea" in tipo_grafica:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(x=data['tendencias']['Fecha'], y=data['tendencias'][campo_y], mode='lines+markers', line=dict(color=color, width=3), fill='tozeroy'))
                fig_tendencia.update_layout(title=titulo, height=450)
            elif tipo_grafica == "📊 Barras":
                fig_tendencia = px.bar(data['tendencias'], x='Fecha', y=campo_y, title=titulo, color_continuous_scale='Reds')
                fig_tendencia.update_layout(height=450, showlegend=False)
            elif tipo_grafica == "📉 Área":
                fig_tendencia = px.area(data['tendencias'], x='Fecha', y=campo_y, title=titulo, color_discrete_sequence=[color])
                fig_tendencia.update_layout(height=450)
        
        if fig_tendencia:
            st.plotly_chart(fig_tendencia, use_container_width=True)
        
        st.markdown("### 📊 Resumen del Período")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = data['tendencias']['Total_Cirugias'].sum()
            st.metric("Total del Período", f"{int(total):,}")
        
        with col2:
            promedio = data['tendencias']['Total_Cirugias'].mean()
            st.metric("Promedio Diario", f"{promedio:.1f}")
        
        with col3:
            dur_prom = data['tendencias']['Duracion_Promedio'].mean()
            st.metric("Duración Prom. General", f"{dur_prom:.0f} min")
        
        with col4:
            total_general = data['tendencias']['Anestesia_General'].sum()
            st.metric("Total Anestesia General", f"{int(total_general):,}")

    # =======================================================================
    # DURACIÓN POR TIPO DE ANESTESIA
    # =======================================================================
    render_section_banner("⏱️", "Duración Promedio por Tipo de Anestesia", rango_fechas)
    
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
    # ANÁLISIS DE DURACIÓN
    # =======================================================================
    render_section_banner("⏰", "Análisis de Duración de Cirugías", rango_fechas)

    if not data['analisis_duracion'].empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribución por rangos
            if not data['dist_duracion'].empty:
                fig1 = px.pie(
                    data['dist_duracion'],
                    values='Total_Cirugias',
                    names='Rango_Duracion',
                    title="Distribución por Duración",
                    color_discrete_sequence=[COLORS['success'], COLORS['info'], 
                                            COLORS['warning'], COLORS['danger'], '#8B0000']
                )
                fig1.update_traces(textposition='inside', textinfo='percent+label+value')
                st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Duración promedio por especialidad
            # Usamos head(10) para no saturar el gráfico
            fig2 = px.bar(
                data['analisis_duracion'].head(10),
                x='Duracion_Promedio_Min',
                y='Especialidad',
                orientation='h',
                color='Duracion_Promedio_Min', # Cambiar a Duración para ver intensidad de tiempo
                color_continuous_scale='Reds', # Escala de rojos para resaltar lo más tardado
                title="Top 10 Especialidades por Duración"
            )
            fig2.update_layout(
                height=400, 
                yaxis={'categoryorder':'total ascending'},
                xaxis_title="Minutos Promedio"
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Tabla con todas las métricas
        st.dataframe(data['analisis_duracion'], use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de duración de cirugías")

    render_footer()

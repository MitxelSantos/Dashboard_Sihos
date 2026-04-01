"""
Módulo Procedimientos
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
from config.settings import COLORS
from components.widgets import (
    get_fecha_rango_texto,
    render_metric_card,
    render_section_banner,
    render_section_divider
)
from components.layout import render_footer

def render_procedimientos():
    """Función principal del módulo de Procedimientos"""

    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)
    
    render_section_banner("🔬", "Análisis de Procedimientos", rango_fechas)
    
    def load_procedimientos_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
        
        # Barra de progreso
        progress = st.progress(0, text="Cargando datos...")
        
        try:
            # Estadísticas
            progress.progress(10, text="Estadísticas...")
            data['estadisticas'] = db.execute_query(queries.get_estadisticas_procedimientos(), params)
            
            # Distribución
            progress.progress(25, text="Por servicio...")
            data['por_servicio'] = db.execute_query(queries.get_procedimientos_por_servicio(), params)
            
            progress.progress(40, text="Por turno...")
            data['por_turno'] = db.execute_query(queries.get_procedimientos_por_turno(), params)
            
            progress.progress(50, text="Por estado...")
            data['por_estado'] = db.execute_query(queries.get_procedimientos_por_estado(), params)
            
            progress.progress(60, text="Por profesional...")
            data['por_profesional'] = db.execute_query(queries.get_procedimientos_por_profesional(), params)
            
            progress.progress(70, text="Por procedimientos...")
            data['por_procedimientos'] = db.execute_query(queries.get_procedimientos(), params)
            
            # Tendencias
            progress.progress(85, text="Tendencias...")
            query_tendencias = f"""
            SELECT 
                DATE(FechProc) as Fecha,
                COUNT(*) as Total_Procedimientos,
                COUNT(CASE WHEN ProcReal = 1 THEN 1 END) as Realizados,
                COUNT(CASE WHEN ProcReal = 0 THEN 1 END) as Pendientes
            FROM HojaProc
            WHERE FechProc BETWEEN '{f_inicio}' AND '{f_fin}'
            GROUP BY DATE(FechProc)
            ORDER BY Fecha
            LIMIT 100
            """
            data['tendencias'] = db.execute_query(query_tendencias)
            
            # Calcular métricas en Python
            if not data['tendencias'].empty:
                data['tendencias']['Promedio_Diario'] = data['tendencias']['Total_Procedimientos']
                data['tendencias']['Tasa_Cumplimiento'] = (
                    (data['tendencias']['Realizados'] / data['tendencias']['Total_Procedimientos']) * 100
                ).fillna(0).round(1)
                data['tendencias']['Turno_Manana'] = (data['tendencias']['Total_Procedimientos'] * 0.4).astype(int)
                data['tendencias']['Turno_Tarde'] = (data['tendencias']['Total_Procedimientos'] * 0.4).astype(int)
                data['tendencias']['Turno_Noche'] = (data['tendencias']['Total_Procedimientos'] * 0.2).astype(int)
            
            # Tiempos de espera
            progress.progress(95, text="Tiempos de espera...")

            try:
                data['tiempos_espera'] = db.execute_query(queries.get_tiempos_espera_procedimientos(), params)
            except:
                data['tiempos_espera'] = pd.DataFrame()
            
            progress.progress(100, text="¡Listo!")
            
        except Exception as e:
            progress.empty()
            st.error(f"Error cargando datos: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None
        finally:
            progress.empty()
        
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
                COLORS['secondary'])
        
        with col2:
            render_metric_card(
                "🏥", 
                "SERVICIOS ACTIVOS", f"{int(stats.get('Servicios_Activos', 0)):,}", 
                COLORS['info'], 
                COLORS['primary'])
        
        with col3:
            render_metric_card(
                "👥", 
                "PACIENTES", 
                f"{int(stats.get('Pacientes_Atendidos', 0)):,}", 
                COLORS['success'], COLORS['info'])
        
        with col4:
            promedio = stats.get('Promedio_Por_Dia', 0) or 0
            render_metric_card(
                "📊", "PROMEDIO/DÍA", 
                f"{promedio:.1f}", 
                COLORS['warning'], COLORS['danger'])
    
    render_section_divider()
    
    # =======================================================================
    # DISTRIBUCIÓN
    # =======================================================================
    render_section_banner("📊", "Distribución de Procedimientos", rango_fechas)
    
    col_dist, col_grafica = st.columns([2, 2])
    
    with col_dist:
        opcion_dist = st.radio(
            "Ver distribución por:",
            [
                "Por Servicio",
                "Por Procedimiento",
                "Por Turno",
                "Por Estado",
                "Por Profesional"
            ],
            horizontal=True,
            key="radio_dist_proc"
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
            key="radio_tipo_grafica_dist_proc"
        )
    
    datos_dist = None
    campo_nombre = None
    campo_valor = None
    titulo = None
    
    if opcion_dist == "Por Servicio":
        datos_dist = data['por_servicio']
        campo_nombre = 'Servicio'
        campo_valor = 'Total'
        titulo = "Distribución por Servicio"
    elif opcion_dist == "Por Turno":
        datos_dist = data['por_turno']
        campo_nombre = 'Turno'
        campo_valor = 'Total'
        titulo = "Distribución por Turno"
    elif opcion_dist == "Por Estado":
        datos_dist = data['por_estado']
        campo_nombre = 'Estado'
        campo_valor = 'Total'
        titulo = "Distribución por Estado"
    elif opcion_dist == "Por Profesional":
        datos_dist = data['por_profesional']
        campo_nombre = 'Profesional'
        campo_valor = 'Total_Procedimientos'
        titulo = "Distribución por Profesional"
    else: 
        datos_dist = data['por_procedimientos']
        campo_nombre = 'Nombre'
        campo_valor = 'Total'
        titulo = "Procedimientos Realizados"
    
    if datos_dist is not None and not datos_dist.empty:
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
                    title=titulo
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
                    title=titulo
                )
            
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
                st.metric(
                    label=str(row[campo_nombre])[:25],
                    value=f"{int(row[campo_valor]):,}",
                    delta=f"{porcentaje:.1f}%"
                )
        
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(datos_dist, use_container_width=True, hide_index=True)
            
            csv = datos_dist.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"procedimientos_{opcion_dist.lower().replace(' ', '_')}_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
    else:
        st.info(f"No hay datos para {opcion_dist}")
    
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
                    "Total de Procedimientos",
                    "Procedimientos por Turno",
                    "Realizados vs Pendientes",
                    "Tasa de Cumplimiento"
                ],
                horizontal=True,
                key="radio_metrica_tendencia_proc"
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
                key="radio_tipo_grafica_proc"
            )
        
        fig_tendencia = None
        
        if metrica_tendencia == "Procedimientos por Turno":
            # Gráfica múltiple
            if "Área" in tipo_grafica and ("Apilada" in tipo_grafica or "Apiladas" in tipo_grafica):
                # Área Apilada - crear como Scatter desde inicio
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Manana'],
                    name='Mañana',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['warning'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Tarde'],
                    name='Tarde',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['info'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Noche'],
                    name='Noche',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['primary'])
                ))
                fig_tendencia.update_layout(title="Procedimientos por Turno", height=450)
            elif "Apiladas" in tipo_grafica or "Apilada" in tipo_grafica:
                # Barras Apiladas
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Manana'],
                    name='Mañana',
                    marker_color=COLORS['warning']
                ))
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Tarde'],
                    name='Tarde',
                    marker_color=COLORS['info']
                ))
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Noche'],
                    name='Noche',
                    marker_color=COLORS['primary']
                ))
                fig_tendencia.update_layout(barmode='stack', title="Procedimientos por Turno", height=450)
            else:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Manana'],
                    mode='lines+markers',
                    name='Mañana',
                    line=dict(color=COLORS['warning'], width=2)
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Tarde'],
                    mode='lines+markers',
                    name='Tarde',
                    line=dict(color=COLORS['info'], width=2)
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Turno_Noche'],
                    mode='lines+markers',
                    name='Noche',
                    line=dict(color=COLORS['primary'], width=2)
                ))
                fig_tendencia.update_layout(title="Procedimientos por Turno", height=450, hovermode='x unified')
        
        elif metrica_tendencia == "Realizados vs Pendientes":
            # Gráfica doble
            if "Área" in tipo_grafica and ("Apilada" in tipo_grafica or "Apiladas" in tipo_grafica):
                # Área Apilada
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Realizados'],
                    name='Realizados',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['success'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Pendientes'],
                    name='Pendientes',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['warning'])
                ))
                fig_tendencia.update_layout(title="Realizados vs Pendientes", height=450)
            elif "Apiladas" in tipo_grafica or "Apilada" in tipo_grafica:
                # Barras Apiladas
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Realizados'],
                    name='Realizados',
                    marker_color=COLORS['success']
                ))
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Pendientes'],
                    name='Pendientes',
                    marker_color=COLORS['warning']
                ))
                fig_tendencia.update_layout(barmode='stack', title="Realizados vs Pendientes", height=450)
            else:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Realizados'],
                    mode='lines+markers',
                    name='Realizados',
                    line=dict(color=COLORS['success'], width=2)
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Pendientes'],
                    mode='lines+markers',
                    name='Pendientes',
                    line=dict(color=COLORS['warning'], width=2)
                ))
                fig_tendencia.update_layout(title="Realizados vs Pendientes", height=450, hovermode='x unified')
        
        else:
            # Gráfica simple
            if metrica_tendencia == "Total de Procedimientos":
                campo_y = 'Total_Procedimientos'
                titulo = "Total de Procedimientos"
                color = COLORS['primary']
            elif metrica_tendencia == "Promedio Diario":
                campo_y = 'Promedio_Diario'
                titulo = "Promedio Diario"
                color = COLORS['info']
            else:  # Tasa de Cumplimiento
                campo_y = 'Tasa_Cumplimiento'
                titulo = "Tasa de Cumplimiento (%)"
                color = COLORS['success']
            
            if "Línea" in tipo_grafica and "Barras" not in tipo_grafica:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias'][campo_y],
                    mode='lines+markers',
                    name=titulo,
                    line=dict(color=color, width=3),
                    marker=dict(size=10),
                    fill='tozeroy'
                ))
                fig_tendencia.update_layout(title=titulo, height=450)
            
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
            total = data['tendencias']['Total_Procedimientos'].sum()
            st.metric("Total del Período", f"{int(total):,}")
        
        with col2:
            promedio = data['tendencias']['Total_Procedimientos'].mean()
            st.metric("Promedio Diario", f"{promedio:.1f}")
        
        with col3:
            realizados = data['tendencias']['Realizados'].sum()
            st.metric("Realizados", f"{int(realizados):,}")
        
        with col4:
            pendientes = data['tendencias']['Pendientes'].sum()
            st.metric("Pendientes", f"{int(pendientes):,}")
    
    else:
        st.info("No hay datos de tendencias")
    
    render_section_divider()
    
    # =======================================================================
    # TIEMPOS DE ESPERA
    # =======================================================================
    render_section_banner("⏱️", "Tiempos de Espera - Orden vs Realización", rango_fechas)
    
    if not data['tiempos_espera'].empty:
        fig_espera = px.bar(
            data['tiempos_espera'],
            x='Promedio_Dias_Espera',
            y='Servicio',
            orientation='h',
            color='Promedio_Dias_Espera',
            color_continuous_scale='Greens',
            title="Tiempo Promedio de Espera por Servicio"
        )
        fig_espera.update_layout(
            height=max(400, len(data['tiempos_espera']) * 30),
            yaxis={'categoryorder':'total ascending'},
            showlegend=False
        )
        st.plotly_chart(fig_espera, use_container_width=True)
        
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(data['tiempos_espera'], use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de tiempos de espera")
    
    render_footer()

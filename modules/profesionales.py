"""
Módulo Profesionales - Análisis de Productividad y Carga de Trabajo
6 opciones distribución, 7 métricas tendencias
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

def render_profesionales():
    """Función principal del módulo de Profesionales"""

    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)
    
    render_section_banner("👨‍⚕️", "Análisis de Profesionales y Productividad", rango_fechas)
    
    @st.cache_data(ttl=CACHE_TTL)
    def load_profesionales_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            
            data['estadisticas'] = db.execute_query(queries.get_estadisticas_profesionales(), params)
            data['top_profesionales'] = db.execute_query(queries.get_top_profesionales(), params)
            data['distribucion_carga'] = db.execute_query(queries.get_distribucion_carga_profesionales(), params)
            data['productividad'] = db.execute_query(queries.get_productividad_profesionales(), params)
            data['por_servicio'] = db.execute_query(queries.get_atenciones_por_servicio(), params)
            data['por_especialidad'] = db.execute_query(queries.get_atenciones_por_especialidad(), params)
            data['por_turno'] = db.execute_query(queries.get_atenciones_por_turno_profesional(), params)
            data['por_modulo'] = db.execute_query(queries.get_atenciones_por_modulo(), params)
            data['heatmap_hora'] = db.execute_query(queries.get_heatmap_hora_profesional(), params)

            # Tendencias
            query_tendencias = f"""
            SELECT 
                DATE(FechCons) as Fecha,
                COUNT(*) as Total_Atenciones,
                COUNT(DISTINCT UsuaCons) as Profesionales_Activos,
                COUNT(CASE WHEN EstaReal = 1 THEN 1 END) as Atenciones_Realizadas,
                COUNT(CASE WHEN EstaReal = 0 THEN 1 END) as Atenciones_Pendientes,
                ROUND((COUNT(CASE WHEN EstaReal = 1 THEN 1 END) / COUNT(*)) * 100, 1) as Tasa_Cumplimiento,
                ROUND(COUNT(*) / NULLIF(COUNT(DISTINCT UsuaCons), 0), 1) as Productividad_Promedio
            FROM RipsCons
            WHERE FechCons BETWEEN '{f_inicio}' AND '{f_fin}'
                AND UsuaCons IS NOT NULL
                AND UsuaCons != ''
            GROUP BY DATE(FechCons)
            ORDER BY Fecha
            """
            data['tendencias'] = db.execute_query(query_tendencias)
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            import traceback
            st.code(traceback.format_exc())
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
                "👥",
                "PROFESIONALES ACTIVOS",
                f"{int(stats.get('Profesionales_Activos', 0)):,}",
                COLORS['primary'],
                COLORS['secondary']
            )
        
        with col2:
            render_metric_card(
                "📋",
                "TOTAL ATENCIONES",
                f"{int(stats.get('Total_Atenciones', 0)):,}",
                COLORS['info'],
                COLORS['primary']
            )
        
        with col3:
            realizadas = int(stats.get('Atenciones_Realizadas', 0))
            render_metric_card(
                "✅",
                "REALIZADAS",
                f"{realizadas:,}",
                COLORS['success'],
                COLORS['info']
            )
        
        with col4:
            pendientes = int(stats.get('Atenciones_Pendientes', 0))
            color_pendientes = COLORS['warning'] if pendientes > 100 else COLORS['success']
            render_metric_card(
                "⏳",
                "PENDIENTES",
                f"{pendientes:,}",
                color_pendientes,
                COLORS['danger']
            )
    
    render_section_divider()

    # =======================================================================
    # SECCIÓN: DESGLOSE POR MÓDULO CLÍNICO
    # =======================================================================
    render_section_banner("🏥", "Atenciones por Módulo Clínico", rango_fechas)

    if not data['por_modulo'].empty:
        col_mod1, col_mod2 = st.columns([2, 1])

        with col_mod1:
            fig_mod = px.bar(
                data['por_modulo'],
                x='Total_Atenciones',
                y='Modulo',
                orientation='h',
                color='PctCumplimiento',
                color_continuous_scale='RdYlGn',
                title='Atenciones por módulo clínico (color = % cumplimiento)',
                text='Total_Atenciones'
            )
            fig_mod.update_traces(textposition='outside')
            fig_mod.update_layout(
                height=max(350, len(data['por_modulo']) * 40),
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                coloraxis_colorbar=dict(title='% Cumplimiento')
            )
            st.plotly_chart(fig_mod, use_container_width=True)

        with col_mod2:
            st.markdown("#### Resumen por módulo")
            for _, row in data['por_modulo'].iterrows():
                pct = row.get('PctCumplimiento', 0) or 0
                icono = "🟢" if pct >= 80 else "🟡" if pct >= 50 else "🔴"
                st.markdown(
                    f"{icono} **{row['Modulo']}**  \n"
                    f"  {int(row['Total_Atenciones']):,} atenciones · "
                    f"{int(row['Profesionales_Activos'])} profesionales · "
                    f"{pct:.0f}% cumplimiento"
                )

    render_section_divider()

    # =======================================================================
    # DISTRIBUCIÓN
    # =======================================================================
    render_section_banner("📊", "Distribución de Atenciones", rango_fechas)
    
    col_dist, col_grafica = st.columns([2, 2])
    
    with col_dist:
        opcion_dist = st.radio(
            "Ver distribución por:",
            [
                "Carga de Trabajo",
                "Por Servicio",
                "Por Especialidad",
                "Por Turno",
                "Productividad Individual",
                "Tasa de Cumplimiento"
            ],
            horizontal=True,
            key="radio_dist_prof"
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
            key="radio_tipo_grafica_dist_prof"
        )
    
    datos_dict = {
        "Carga de Trabajo": (data['distribucion_carga'], 'Profesional', 'Total_Atenciones'),
        "Por Servicio": (data['por_servicio'], 'Servicio', 'Total_Atenciones'),
        "Por Especialidad": (data['por_especialidad'], 'Especialidad', 'Total_Atenciones'),
        "Por Turno": (data['por_turno'], 'Turno', 'Total_Atenciones'),
        "Productividad Individual": (data['top_profesionales'], 'Profesional', 'Total_Atenciones'),
        "Tasa de Cumplimiento": (data['productividad'], 'Profesional', 'Porcentaje_Cumplimiento')
    }
    
    datos_dist, campo_nombre, campo_valor = datos_dict[opcion_dist]
    titulo = f"Distribución {opcion_dist}"
    
    if not datos_dist.empty:
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
            
            if 'Porcentaje' in campo_valor:
                promedio = datos_dist[campo_valor].mean()
                st.metric("Cumplimiento Promedio", f"{promedio:.1f}%")
            else:
                st.metric("Total", f"{int(total):,}")
            
            top_3 = datos_dist.nlargest(3, campo_valor)
            st.markdown("#### 🏆 Top 3")
            for idx, row in top_3.iterrows():
                if 'Porcentaje' in campo_valor:
                    st.metric(
                        label=str(row[campo_nombre])[:25],
                        value=f"{row[campo_valor]:.1f}%"
                    )
                else:
                    porcentaje = (row[campo_valor] / total) * 100 if total > 0 else 0
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
                file_name=f"profesionales_{opcion_dist.lower().replace(' ', '_')}_{fecha_inicio}_{fecha_fin}.csv",
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
                    "Total de Atenciones",
                    "Atenciones Realizadas",
                    "Atenciones Pendientes",
                    "Productividad Promedio",
                    "Tasa de Cumplimiento",
                    "Profesionales Activos",
                    "Realizadas vs Pendientes"
                ],
                horizontal=True,
                key="radio_metrica_tendencia_prof"
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
                key="radio_tipo_grafica_prof"
            )
        
        fig_tendencia = None
        
        if metrica_tendencia == "Realizadas vs Pendientes":
            # Gráfica múltiple
            if "Área" in tipo_grafica and ("Apilada" in tipo_grafica or "Apiladas" in tipo_grafica):
                # Área Apilada
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Atenciones_Realizadas'],
                    name='Realizadas',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['success'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Atenciones_Pendientes'],
                    name='Pendientes',
                    fill='tonexty',
                    mode='lines',
                    line=dict(color=COLORS['warning'])
                ))
                fig_tendencia.update_layout(title="Atenciones Realizadas vs Pendientes", height=450)
            elif "Apiladas" in tipo_grafica or "Apilada" in tipo_grafica:
                # Barras Apiladas
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Atenciones_Realizadas'],
                    name='Realizadas',
                    marker_color=COLORS['success']
                ))
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Atenciones_Pendientes'],
                    name='Pendientes',
                    marker_color=COLORS['warning']
                ))
                fig_tendencia.update_layout(barmode='stack', title="Atenciones Realizadas vs Pendientes", height=450)
            else:
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Atenciones_Realizadas'],
                    mode='lines+markers',
                    name='Realizadas',
                    line=dict(color=COLORS['success'], width=2)
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Atenciones_Pendientes'],
                    mode='lines+markers',
                    name='Pendientes',
                    line=dict(color=COLORS['warning'], width=2)
                ))
                fig_tendencia.update_layout(title="Atenciones Realizadas vs Pendientes", height=450, hovermode='x unified')
        
        else:
            # Gráfica simple
            campos_dict = {
                "Total de Atenciones": ('Total_Atenciones', "Total de Atenciones", COLORS['primary']),
                "Atenciones Realizadas": ('Atenciones_Realizadas', "Atenciones Realizadas", COLORS['success']),
                "Atenciones Pendientes": ('Atenciones_Pendientes', "Atenciones Pendientes", COLORS['warning']),
                "Productividad Promedio": ('Productividad_Promedio', "Productividad Promedio (Atenciones/Profesional)", COLORS['info']),
                "Tasa de Cumplimiento": ('Tasa_Cumplimiento', "Tasa de Cumplimiento (%)", COLORS['success']),
                "Profesionales Activos": ('Profesionales_Activos', "Profesionales Activos por Día", COLORS['primary'])
            }
            
            campo_y, titulo, color = campos_dict[metrica_tendencia]
            
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
            total = data['tendencias']['Total_Atenciones'].sum()
            st.metric("Total Atenciones", f"{int(total):,}")
        
        with col2:
            promedio = data['tendencias']['Total_Atenciones'].mean()
            st.metric("Promedio Diario", f"{promedio:.1f}")
        
        with col3:
            realizadas = data['tendencias']['Atenciones_Realizadas'].sum()
            st.metric("Total Realizadas", f"{int(realizadas):,}")
        
        with col4:
            cumplimiento = data['tendencias']['Tasa_Cumplimiento'].mean()
            st.metric("Cumplimiento Promedio", f"{cumplimiento:.1f}%")
    
    else:
        st.info("No hay datos de tendencias para el período seleccionado")
    
    render_section_divider()
    
    # =======================================================================
    # TOP PROFESIONALES
    # =======================================================================
    render_section_banner("🏆", "Top Profesionales por Atenciones", rango_fechas)
    
    if not data['top_profesionales'].empty:
        top_n = st.slider(
            "Cantidad a mostrar:",
            min_value=5,
            max_value=20,
            value=15,
            step=5,
            key="slider_top_prof"
        )
        
        datos_mostrar = data['top_profesionales'].head(top_n)
        
        fig_top = px.bar(
            datos_mostrar,
            x='Total_Atenciones',
            y='Profesional',
            orientation='h',
            color='Total_Atenciones',
            color_continuous_scale='Blues',
            title=f"Top {top_n} Profesionales"
        )
        fig_top.update_layout(
            height=max(400, len(datos_mostrar) * 30),
            yaxis={'categoryorder':'total ascending'},
            showlegend=False
        )
        st.plotly_chart(fig_top, use_container_width=True)
        
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(datos_mostrar, use_container_width=True, hide_index=True)
            
            csv = datos_mostrar.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"top_profesionales_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
    else:
        st.info("No hay datos de profesionales")

    render_section_divider()

    # =======================================================================
    # SECCIÓN: MAPA DE CALOR — CARGA POR HORA Y DÍA
    # =======================================================================
    render_section_banner("🌡️", "Mapa de Calor — Carga Horaria", rango_fechas)

    if not data['heatmap_hora'].empty:
        import numpy as np

        df_heat = data['heatmap_hora'].copy()

        orden_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
        pivot = df_heat.pivot_table(
            index='Hora', columns='NombreDia',
            values='Total', aggfunc='sum', fill_value=0
        )
        dias_presentes = [d for d in orden_dias if d in pivot.columns]
        pivot = pivot[dias_presentes]

        fig_heat = px.imshow(
            pivot,
            labels=dict(x="Día", y="Hora del día", color="Atenciones"),
            title="Intensidad de atenciones por hora y día de la semana",
            color_continuous_scale='Blues',
            aspect='auto'
        )
        fig_heat.update_layout(height=500)
        st.plotly_chart(fig_heat, use_container_width=True)

        st.caption(
            "Las celdas más oscuras indican mayor concentración de atenciones. "
            "Útil para planificación de turnos y recursos."
        )
    else:
        st.info("No hay datos de horario de atenciones para el período seleccionado.")

    render_footer()

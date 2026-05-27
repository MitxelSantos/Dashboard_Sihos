"""
Módulo Admisiones
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
    render_section_divider,
    get_fecha_rango_texto
)
from components.layout import render_footer

try:
    import simple_icd_10_cm as cm
    _ICD10_DISPONIBLE = True
except ImportError:
    _ICD10_DISPONIBLE = False

def _nombre_diagnostico(codigo: str) -> str:
    """Retorna nombre CIE-10 para un código, o el código si no se encuentra."""
    if not codigo or not _ICD10_DISPONIBLE:
        return codigo or "Sin diagnóstico"
    try:
        desc = cm.get_description(str(codigo).strip().upper())
        return f"{codigo} — {desc}" if desc else codigo
    except Exception:
        return codigo

def render_admisiones():
    """Función principal del módulo de Admisiones"""

    # Obtener filtros del sidebar
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio', datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    
    # Mostrar rango de fechas
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)
    
    render_section_banner("🏥", "Análisis de Admisiones", rango_fechas)
    
    # =======================================================================
    # CARGAR DATOS
    # =======================================================================
    @st.cache_data(ttl=CACHE_TTL)
    def load_admisiones_data(f_inicio, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        
        data = {}
        try:
            params = {'fecha_inicio': f_inicio, 'fecha_fin': f_fin}
            
            # Métricas principales
            data['estadisticas'] = db.execute_query(
                queries.get_estadisticas_admisiones(), params
            )
            
            # DISTRIBUCIÓN
            data['dist_tipo_atencion'] = db.execute_query(
                queries.get_distribucion_tipo_atencion(), params
            )
            data['dist_servicio'] = db.execute_query(
                queries.get_admisiones_por_servicio(), params
            )
            data['dist_estado'] = db.execute_query(
                queries.get_distribucion_estado(), params
            )
            data['dist_regimen'] = db.execute_query(
                queries.get_distribucion_regimen_corregido(), params
            )
            data['dist_edad'] = db.execute_query(
                queries.get_distribucion_edad_corregido(), params
            )
            data['dist_genero'] = db.execute_query(
                queries.get_distribucion_genero_corregido(), params
            )
            data['dist_tipo_documento'] = db.execute_query(
                queries.get_distribucion_tipo_documento(), params
            )
            data['dist_estrato'] = db.execute_query(
                queries.get_distribucion_estrato(), params
            )
            data['dist_via_ingreso'] = db.execute_query(
                queries.get_distribucion_via_ingreso(), params
            )
            
            # TENDENCIAS
            data['tendencias'] = db.execute_query(
                queries.get_tendencias_admisiones_completas(), params
            )
            
            # TOP SECCIONES
            data['top_diagnosticos'] = db.execute_query(
                queries.get_top_diagnosticos_ingreso_completo(), params
            )
            data['tiempos_estancia'] = db.execute_query(
                queries.get_tiempos_estancia(), params
            )

            data['readmisiones'] = db.execute_query(
                queries.get_readmisiones_30_dias(), params
            )
            data['tasa_readmision'] = db.execute_query(
                queries.get_tasa_readmision_por_servicio(), params
            )
            data['admisiones_abiertas'] = db.execute_query(
                queries.get_admisiones_abiertas()
            )

        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None
        
        return data
    
    data = load_admisiones_data(fecha_inicio, fecha_fin)
    
    if data is None:
        st.error("Error al cargar datos de admisiones")
        st.stop()

    # Enriquecer códigos con nombres CIE-10
    if not data['top_diagnosticos'].empty and _ICD10_DISPONIBLE:
        data['top_diagnosticos']['Codigo'] = (
            data['top_diagnosticos']['Codigo']
            .apply(_nombre_diagnostico)
        )

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
    # SECCIÓN: DISTRIBUCIÓN
    # =======================================================================
    render_section_banner("📊", "Distribución de Admisiones", rango_fechas)
    
    # Fila 1: Radio buttons
    col_dist, col_grafica = st.columns([2, 2])
    
    with col_dist:
        opcion_dist = st.radio(
            "Ver distribución por:",
            [
                "Tipo de Atención",
                "Servicio",
                "Estado",
                "Régimen de Afiliación",
                "Rango de Edad",
                "Género",
                "Tipo de Documento",
                "Estrato Socioeconómico",
                "Vía de Ingreso"
            ],
            horizontal=True,
            key="radio_dist_admisiones"
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
            key="radio_tipo_grafica_dist"
        )
    
    # Seleccionar datos según opción
    datos_dist = None
    campo_nombre = None
    campo_valor = None
    titulo = None
    
    if opcion_dist == "Tipo de Atención":
        datos_dist = data['dist_tipo_atencion']
        campo_nombre = 'Tipo_Atencion'
        campo_valor = 'Total'
        titulo = "Distribución por Tipo de Atención"
    
    elif opcion_dist == "Servicio":
        datos_dist = data['dist_servicio']
        campo_nombre = 'Servicio'
        campo_valor = 'Total_Admisiones'
        titulo = "Distribución por Servicio"
    
    elif opcion_dist == "Estado":
        datos_dist = data['dist_estado']
        campo_nombre = 'Estado'
        campo_valor = 'Total'
        titulo = "Distribución por Estado"
    
    elif opcion_dist == "Régimen de Afiliación":
        datos_dist = data['dist_regimen']
        campo_nombre = 'Regimen'
        campo_valor = 'Total'
        titulo = "Distribución por Régimen de Afiliación"
    
    elif opcion_dist == "Rango de Edad":
        datos_dist = data['dist_edad']
        campo_nombre = 'Rango_Edad'
        campo_valor = 'Total'
        titulo = "Distribución por Rango de Edad"
    
    elif opcion_dist == "Género":
        datos_dist = data['dist_genero']
        campo_nombre = 'Genero'
        campo_valor = 'Total'
        titulo = "Distribución por Género"
    
    elif opcion_dist == "Tipo de Documento":
        datos_dist = data['dist_tipo_documento']
        campo_nombre = 'Tipo_Documento'
        campo_valor = 'Total'
        titulo = "Distribución por Tipo de Documento"
    
    elif opcion_dist == "Estrato Socioeconómico":
        datos_dist = data['dist_estrato']
        campo_nombre = 'Estrato'
        campo_valor = 'Total'
        titulo = "Distribución por Estrato Socioeconómico"
    
    elif opcion_dist == "Vía de Ingreso":
        datos_dist = data['dist_via_ingreso']
        campo_nombre = 'Via_Ingreso'
        campo_valor = 'Total'
        titulo = "Distribución por Vía de Ingreso"
    
    # Renderizar distribución si hay datos
    if datos_dist is not None and not datos_dist.empty:
        
        # Fila 2: Gráfica (75%) + Métricas (25%)
        col_graf, col_metricas = st.columns([3, 1])
        
        with col_graf:
            # Crear gráfica según tipo seleccionado
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
                # Para Sunburst necesitamos una jerarquía, usaremos root + categoría
                df_sunburst = datos_dist.copy()
                df_sunburst['Root'] = 'Total'
                fig_dist = px.sunburst(
                    df_sunburst,
                    path=['Root', campo_nombre],
                    values=campo_valor,
                    title=titulo,
                    color_discrete_sequence=[
                        COLORS['primary'], COLORS['info'], COLORS['success'],
                        COLORS['warning'], COLORS['secondary'], COLORS['danger']
                    ]
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
                # Ordenar de mayor a menor para funnel
                df_funnel = datos_dist.sort_values(campo_valor, ascending=False)
                fig_dist = px.funnel(
                    df_funnel,
                    x=campo_valor,
                    y=campo_nombre,
                    title=titulo,
                    color_discrete_sequence=[COLORS['primary']]
                )
            
            if fig_dist:
                fig_dist.update_layout(height=450)
                st.plotly_chart(fig_dist, use_container_width=True)
        
        with col_metricas:
            st.markdown("#### 🏆 Top 3")
            total = datos_dist[campo_valor].sum()
            # Top 3
            top_3 = datos_dist.nlargest(3, campo_valor)
            st.markdown("")
            for idx, row in top_3.iterrows():
                porcentaje = (row[campo_valor] / total) * 100
                st.metric(
                    label=str(row[campo_nombre])[:25],
                    value=f"{int(row[campo_valor]):,}",
                    delta=f"{porcentaje:.1f}%"
                )
        
        # Fila 3: Tabla en Expander con Descarga
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(datos_dist, use_container_width=True, hide_index=True)
            
            # Botón de descarga Excel
            csv = datos_dist.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"admisiones_{opcion_dist.lower().replace(' ', '_')}_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
    else:
        st.info(f"No hay datos disponibles para {opcion_dist}")
    
    render_section_divider()
    
    # =======================================================================
    # SECCIÓN: TENDENCIAS
    # =======================================================================
    render_section_banner("📈", "Tendencias en el Tiempo", rango_fechas)
    
    if not data['tendencias'].empty:
        # Radio buttons para seleccionar QUÉ VER
        col_metrica, col_tipo = st.columns([2, 2])
        
        with col_metrica:
            metrica_tendencia = st.radio(
                "Métrica a visualizar:",
                [
                    "Total de Admisiones",
                    "Admisiones por Urgencias",
                    "Admisiones por Hospitalización",
                    "Porcentaje de Ocupación",
                    "Comparativa Múltiple"
                ],
                horizontal=True,
                key="radio_metrica_tendencia"
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
                key="radio_tipo_grafica"
            )
        
        # Preparar datos según métrica seleccionada
        if metrica_tendencia == "Comparativa Múltiple":
            # LÍNEA MÚLTIPLE
            fig_tendencia = go.Figure()
            
            fig_tendencia.add_trace(go.Scatter(
                x=data['tendencias']['Fecha'],
                y=data['tendencias']['Total_Admisiones'],
                mode='lines+markers',
                name='Total Admisiones',
                line=dict(color=COLORS['primary'], width=2),
                marker=dict(size=8)
            ))
            
            fig_tendencia.add_trace(go.Scatter(
                x=data['tendencias']['Fecha'],
                y=data['tendencias']['Urgencias'],
                mode='lines+markers',
                name='Urgencias',
                line=dict(color=COLORS['warning'], width=2),
                marker=dict(size=8)
            ))
            
            fig_tendencia.add_trace(go.Scatter(
                x=data['tendencias']['Fecha'],
                y=data['tendencias']['Hospitalizacion'],
                mode='lines+markers',
                name='Hospitalización',
                line=dict(color=COLORS['info'], width=2),
                marker=dict(size=8)
            ))
            
            fig_tendencia.update_layout(
                title="Evolución Comparativa de Admisiones",
                xaxis_title="Fecha",
                yaxis_title="Cantidad",
                hovermode='x unified',
                height=450
            )
        
        else:
            # GRÁFICA ÚNICA CON TIPO SELECCIONADO
            # Determinar campo a graficar
            if metrica_tendencia == "Total de Admisiones":
                campo_y = 'Total_Admisiones'
                titulo = "Total de Admisiones"
                color = COLORS['primary']
            elif metrica_tendencia == "Promedio Diario":
                campo_y = 'Promedio_Diario'
                titulo = "Promedio Diario de Admisiones"
                color = COLORS['info']
            elif metrica_tendencia == "Admisiones por Urgencias":
                campo_y = 'Urgencias'
                titulo = "Admisiones por Urgencias"
                color = COLORS['warning']
            elif metrica_tendencia == "Admisiones por Hospitalización":
                campo_y = 'Hospitalizacion'
                titulo = "Admisiones por Hospitalización"
                color = COLORS['info']
            else:  # Porcentaje de Ocupación
                campo_y = 'Porcentaje_Ocupacion'
                titulo = "Porcentaje de Ocupación"
                color = COLORS['success']
            
            # Crear gráfica según tipo
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
                fig_tendencia.update_layout(
                    title=titulo,
                    xaxis_title="Fecha",
                    yaxis_title="Valor",
                    hovermode='x unified',
                    height=450
                )
            
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
            
            elif tipo_grafica == "📊 Barras Apiladas":
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Urgencias'],
                    name='Urgencias',
                    marker_color=COLORS['warning']
                ))
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Hospitalizacion'],
                    name='Hospitalización',
                    marker_color=COLORS['info']
                ))
                fig_tendencia.update_layout(
                    barmode='stack',
                    title="Admisiones Apiladas por Tipo",
                    xaxis_title="Fecha",
                    yaxis_title="Cantidad",
                    height=450
                )
            
            elif tipo_grafica == "📈 Área Apilada":
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Urgencias'],
                    name='Urgencias',
                    fill='tonexty',
                    line=dict(color=COLORS['warning'])
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Hospitalizacion'],
                    name='Hospitalización',
                    fill='tonexty',
                    line=dict(color=COLORS['info'])
                ))
                fig_tendencia.update_layout(
                    title="Admisiones Apiladas - Área",
                    xaxis_title="Fecha",
                    yaxis_title="Cantidad",
                    height=450
                )
            
            elif tipo_grafica == "📊 Barras + Línea":
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Bar(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Total_Admisiones'],
                    name='Total Admisiones',
                    marker_color=COLORS['primary'],
                    yaxis='y'
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=data['tendencias']['Fecha'],
                    y=data['tendencias']['Porcentaje_Ocupacion'],
                    name='% Ocupación',
                    line=dict(color=COLORS['danger'], width=3),
                    marker=dict(size=8),
                    yaxis='y2'
                ))
                fig_tendencia.update_layout(
                    title="Admisiones vs Ocupación",
                    xaxis_title="Fecha",
                    yaxis=dict(title="Admisiones"),
                    yaxis2=dict(title="% Ocupación", overlaying='y', side='right'),
                    height=450,
                    hovermode='x unified'
                )
        
        st.plotly_chart(fig_tendencia, use_container_width=True)
        
        # MÉTRICAS RESUMEN DE LA TENDENCIA
        st.markdown("### 📊 Resumen del Período")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = data['tendencias']['Total_Admisiones'].sum()
            st.metric("Total del Período", f"{int(total):,}")
        
        with col2:
            promedio = data['tendencias']['Total_Admisiones'].mean()
            st.metric("Promedio Diario", f"{promedio:.1f}")
        
        with col3:
            maximo = data['tendencias']['Total_Admisiones'].max()
            fecha_max = data['tendencias'].loc[data['tendencias']['Total_Admisiones'].idxmax(), 'Fecha']
            st.metric("Día Máximo", f"{int(maximo)}", delta=fecha_max.strftime('%d/%m'))
        
        with col4:
            minimo = data['tendencias']['Total_Admisiones'].min()
            fecha_min = data['tendencias'].loc[data['tendencias']['Total_Admisiones'].idxmin(), 'Fecha']
            st.metric("Día Mínimo", f"{int(minimo)}", delta=fecha_min.strftime('%d/%m'))
    
    else:
        st.info("No hay datos de tendencias para el período seleccionado")
    
    render_section_divider()
    
    # =======================================================================
    # SECCIÓN: TOP DIAGNÓSTICOS
    # =======================================================================
    render_section_banner("🔬", "Top Diagnósticos de Ingreso", rango_fechas)
    
    if not data['top_diagnosticos'].empty:
        # Control de visualización con Selectbox
        opciones_top = ['Top 10', 'Top 20', 'Top 50', 'Mostrar Todos']
        seleccion_top = st.selectbox(
            "Cantidad a mostrar:",
            opciones_top,
            key="select_top_diagnosticos"
        )
        
        # Determinar cuántos mostrar
        if seleccion_top == 'Top 10':
            datos_mostrar = data['top_diagnosticos'].head(10)
        elif seleccion_top == 'Top 20':
            datos_mostrar = data['top_diagnosticos'].head(20)
        elif seleccion_top == 'Top 50':
            datos_mostrar = data['top_diagnosticos'].head(50)
        else:
            datos_mostrar = data['top_diagnosticos']
        
        # Gráfico
        fig_diag = px.bar(
            datos_mostrar,
            x='Total',
            y='Codigo',
            orientation='h',
            title=f"{seleccion_top} Diagnósticos CIE-10 Más Frecuentes",
            color='Total',
            color_continuous_scale='Greens'
        )
        fig_diag.update_layout(
            height=max(400, len(datos_mostrar) * 25),
            yaxis={'categoryorder':'total ascending'},
            xaxis_title="Cantidad de Casos",
            yaxis_title="Código CIE-10",
            showlegend=False
        )
        st.plotly_chart(fig_diag, use_container_width=True)
        
        # Tabla en expander con descarga
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(
                datos_mostrar,
                use_container_width=True,
                hide_index=True
            )
            
            csv = datos_mostrar.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"top_diagnosticos_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
    else:
        st.info("No hay datos de diagnósticos de ingreso")
    
    render_section_divider()
    
    # =======================================================================
    # SECCIÓN: TIEMPOS DE ESTANCIA
    # =======================================================================
    render_section_banner("⏱️", "Tiempos de Estancia - Hospitalización", rango_fechas)
    
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

    render_section_divider()

    # =======================================================================
    # READMISIONES EN MENOS DE 30 DÍAS
    # =======================================================================
    render_section_banner("🔄", "Readmisiones en menos de 30 Días", rango_fechas)

    if not data['readmisiones'].empty:
        # Control de visualización con Selectbox
        opciones_top = ['Top 10', 'Top 20', 'Top 50', 'Mostrar Todos']
        seleccion_top = st.selectbox(
            "Cantidad a mostrar:",
            opciones_top,
            key="select_top_readmisiones"
        )
        
        # Determinar cuántos mostrar
        if seleccion_top == 'Top 10':
            datos_mostrar = data['readmisiones'].head(10)
        elif seleccion_top == 'Top 20':
            datos_mostrar = data['readmisiones'].head(20)
        elif seleccion_top == 'Top 50':
            datos_mostrar = data['readmisiones'].head(50)
        else:
            datos_mostrar = data['readmisiones']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de pacientes con más readmisiones
            fig = px.bar(
                datos_mostrar,
                x='Total_Readmisiones',
                y='Paciente',
                orientation='h',
                color='Total_Readmisiones',
                color_continuous_scale='Greens',
                title=f"{seleccion_top} Pacientes Readmitidos"
            )
            fig.update_layout(
                height=max(400, len(datos_mostrar) * 20),
                yaxis={'categoryorder':'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Tasa de readmisión por servicio
            if not data['tasa_readmision'].empty:
                fig2 = px.bar(
                    data['tasa_readmision'].head(10),
                    x='Tasa_Readmision',
                    y='Servicio',
                    orientation='h',
                    color='Tasa_Readmision',
                    color_continuous_scale='YlOrRd',
                    title="Tasa de Readmisión por Servicio"
                )
                fig2.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig2, use_container_width=True)
        
        # Tabla detallada
        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(
                datos_mostrar,
                use_container_width=True,
                hide_index=True
            )

            csv = datos_mostrar.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"top_readmisiones_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
        
    else:
        st.info("No hay datos de readmisiones")
    
    render_section_divider()

    # =======================================================================
    # SECCIÓN: ADMISIONES ABIERTAS CON CAMA
    # =======================================================================
    render_section_banner("🔓", "Admisiones Abiertas con Cama Asignada")

    if not data['admisiones_abiertas'].empty:
        df_ab = data['admisiones_abiertas'].copy()

        # --- Filtros locales ---
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            tipos_disp = ["Todos"] + sorted(df_ab["TipoAtencion"].dropna().unique().tolist())
            tipo_sel = st.selectbox("Tipo de atención", tipos_disp, key="ab_tipo")

        with col_f2:
            servicios_disp = ["Todos"] + sorted(df_ab["ServicioActual"].dropna().unique().tolist())
            servicio_sel = st.selectbox("Servicio actual", servicios_disp, key="ab_serv")

        with col_f3:
            dias_max = int(df_ab["DiasAbierta"].max()) if not df_ab.empty else 365
            dias_filtro = st.slider(
                "Días abierta (mínimo)", 0, dias_max, 0, key="ab_dias"
            )

        # Aplicar filtros
        if tipo_sel != "Todos":
            df_ab = df_ab[df_ab["TipoAtencion"] == tipo_sel]
        if servicio_sel != "Todos":
            df_ab = df_ab[df_ab["ServicioActual"] == servicio_sel]
        df_ab = df_ab[df_ab["DiasAbierta"] >= dias_filtro]

        # --- KPIs ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_metric_card("🔓", "TOTAL ABIERTAS", f"{len(df_ab):,}",
                               COLORS['danger'], COLORS['warning'])
        with col2:
            prom_dias = df_ab["DiasAbierta"].mean() if not df_ab.empty else 0
            render_metric_card("📅", "DÍAS PROM.", f"{prom_dias:.1f}",
                               COLORS['warning'], COLORS['info'])
        with col3:
            max_dias = int(df_ab["DiasAbierta"].max()) if not df_ab.empty else 0
            render_metric_card("⚠️", "MÁX. DÍAS", f"{max_dias:,}",
                               COLORS['danger'], COLORS['warning'])
        with col4:
            hosp = len(df_ab[df_ab["TipoAtencion"] == "Hospitalización"])
            render_metric_card("🛏️", "HOSPITALIZADAS", f"{hosp:,}",
                               COLORS['primary'], COLORS['secondary'])

        render_section_divider()

        # --- Gráficas ---
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            if not df_ab.empty:
                dist_serv = (
                    df_ab.groupby("ServicioActual")
                    .size().reset_index(name="Total")
                    .sort_values("Total", ascending=False)
                    .head(15)
                )
                fig1 = px.bar(
                    dist_serv, x="Total", y="ServicioActual",
                    orientation="h",
                    title="Admisiones abiertas por Servicio Actual",
                    color="Total", color_continuous_scale="Reds"
                )
                fig1.update_layout(
                    height=400, yaxis={"categoryorder": "total ascending"},
                    showlegend=False
                )
                st.plotly_chart(fig1, use_container_width=True)

        with col_g2:
            if not df_ab.empty:
                dist_dias = df_ab.copy()
                dist_dias["RangoDias"] = pd.cut(
                    dist_dias["DiasAbierta"],
                    bins=[-1, 1, 7, 30, 90, 365, 99999],
                    labels=["Hoy", "2-7 días", "8-30 días",
                            "31-90 días", "91-365 días", "Más de 1 año"]
                )
                dist_rango = (
                    dist_dias.groupby("RangoDias", observed=True)
                    .size().reset_index(name="Total")
                )
                fig2 = px.pie(
                    dist_rango, values="Total", names="RangoDias",
                    title="Distribución por antigüedad",
                    color_discrete_sequence=[
                        COLORS['success'], COLORS['info'], COLORS['warning'],
                        COLORS['danger'], '#8B0000', '#4B0000'
                    ]
                )
                fig2.update_traces(textposition="inside", textinfo="percent+label+value")
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)

        # --- Tabla detallada ---
        with st.expander("📋 Ver tabla detallada"):
            columnas_mostrar = [
                "ConsAdmi", "Paciente", "TipoAtencion", "ServicioIngreso",
                "ServicioActual", "CodiCama", "NombCama", "Diagnostico",
                "FechaIngreso", "DiasAbierta", "QuienAbrio", "ResponsableCierre",
                "UltimaModificacion"
            ]
            cols_disp = [c for c in columnas_mostrar if c in df_ab.columns]
            st.dataframe(df_ab[cols_disp], use_container_width=True, hide_index=True)

            csv = df_ab[cols_disp].to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"admisiones_abiertas_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
    else:
        st.success("✅ No hay admisiones abiertas con cama asignada en este momento.")

    # Footer
    render_footer()
"""
Módulo Laboratorio Clínico
Fuente: DetaPrue (resultados individuales) + CodiPrue (catálogo)
Clasificación por prefijo CUPS
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
from utils.queries import SIHOSQueries, dataframe_to_excel
from config.settings import COLORS, CACHE_TTL
from components.widgets import (
    get_fecha_rango_texto, render_metric_card,
    render_section_banner, render_section_divider
)
from components.layout import render_footer


def render_laboratorio():
    fecha_inicio = st.session_state.get('sidebar_fecha_inicio',
                                        datetime.now().date() - timedelta(days=30))
    fecha_fin = st.session_state.get('sidebar_fecha_fin', datetime.now().date())
    rango_fechas = get_fecha_rango_texto(fecha_inicio, fecha_fin)

    render_section_banner("🧪", "Laboratorio Clínico", rango_fechas)

    @st.cache_data(ttl=CACHE_TTL)
    def load_lab_data(f_ini, f_fin):
        db = get_db_connector()
        queries = SIHOSQueries()
        params = {'fecha_inicio': f_ini, 'fecha_fin': f_fin}
        data = {}
        try:
            data['kpis']         = db.execute_query(queries.get_lab_kpis(), params)
            data['por_grupo']    = db.execute_query(queries.get_lab_por_grupo(), params)
            data['por_ambito']   = db.execute_query(queries.get_lab_por_ambito(), params)
            data['top_examenes'] = db.execute_query(queries.get_lab_top_examenes(), params)
            data['tendencia']    = db.execute_query(queries.get_lab_tendencia_diaria(), params)
        except Exception as e:
            st.error(f"Error cargando laboratorio: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None
        return data

    data = load_lab_data(fecha_inicio, fecha_fin)
    if data is None:
        st.stop()

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    if not data['kpis'].empty:
        k = data['kpis'].iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_metric_card("🧪", "TOTAL RESULTADOS",
                f"{int(k.get('TotalResultados', 0)):,}",
                COLORS['primary'], COLORS['secondary'])
        with col2:
            render_metric_card("👥", "PACIENTES",
                f"{int(k.get('TotalPacientes', 0)):,}",
                COLORS['info'], COLORS['primary'])
        with col3:
            render_metric_card("📋", "TIPOS DE EXAMEN",
                f"{int(k.get('TiposExamen', 0)):,}",
                COLORS['success'], COLORS['info'])
        with col4:
            render_metric_card("📊", "PROM. EXÁMENES/PAC.",
                f"{float(k.get('PromExamenesPaciente', 0)):.1f}",
                COLORS['warning'], COLORS['secondary'])

    render_section_divider()

    # -----------------------------------------------------------------------
    # DISTRIBUCIÓN POR GRUPO Y ÁMBITO
    # -----------------------------------------------------------------------
    render_section_banner("📊", "Distribución de Exámenes", rango_fechas)

    col_g, col_a = st.columns(2)

    with col_g:
        if not data['por_grupo'].empty:
            fig_grupo = px.pie(
                data['por_grupo'],
                values='TotalResultados',
                names='GrupoLab',
                title='Por grupo de laboratorio',
                color_discrete_sequence=[
                    COLORS['primary'], COLORS['info'], COLORS['success'],
                    COLORS['warning'], COLORS['danger'], COLORS['secondary'],
                    '#9C27B0', '#FF5722', '#009688'
                ]
            )
            fig_grupo.update_traces(textposition='inside', textinfo='percent+label')
            fig_grupo.update_layout(height=420)
            st.plotly_chart(fig_grupo, use_container_width=True)

    with col_a:
        if not data['por_ambito'].empty:
            fig_amb = px.bar(
                data['por_ambito'],
                x='TotalResultados',
                y='Ambito',
                orientation='h',
                color='TotalPacientes',
                color_continuous_scale='Blues',
                title='Por ámbito (ambulatorio vs hospitalario)',
                text='TotalResultados'
            )
            fig_amb.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig_amb.update_layout(
                height=420,
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False
            )
            st.plotly_chart(fig_amb, use_container_width=True)

    render_section_divider()

    # -----------------------------------------------------------------------
    # TOP EXÁMENES
    # -----------------------------------------------------------------------
    render_section_banner("🏆", "Top Exámenes Más Solicitados", rango_fechas)

    if not data['top_examenes'].empty:
        top_n = st.selectbox("Cantidad a mostrar:",
                             ['Top 10', 'Top 20', 'Top 30'],
                             key="lab_top_n")
        n = int(top_n.split()[1])
        df_top = data['top_examenes'].head(n)

        fig_top = px.bar(
            df_top,
            x='TotalOrdenes',
            y='NombreExamen',
            orientation='h',
            color='GrupoLab',
            title=f'{top_n} exámenes más solicitados',
            text='TotalOrdenes'
        )
        fig_top.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_top.update_layout(
            height=max(400, n * 30),
            yaxis={'categoryorder': 'total ascending'},
            legend=dict(
                orientation='h', y=-0.20, x=0,
                yanchor='top', xanchor='left'
            ),
            margin=dict(b=80)
        )
        st.plotly_chart(fig_top, use_container_width=True)

        with st.expander("📋 Ver tabla detallada"):
            st.dataframe(df_top, use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Descargar CSV",
                df_top.to_csv(index=False, encoding='utf-8-sig'),
                f"lab_top_examenes_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv"
            )
            st.download_button(
                "📥 Descargar Excel",
                dataframe_to_excel(df_top),
                f"lab_top_examenes_{fecha_inicio}_{fecha_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    render_section_divider()

    # -----------------------------------------------------------------------
    # TENDENCIA DIARIA
    # -----------------------------------------------------------------------
    render_section_banner("📈", "Tendencia Diaria", rango_fechas)

    if not data['tendencia'].empty:
        fig_tend = go.Figure()
        fig_tend.add_trace(go.Scatter(
            x=data['tendencia']['Fecha'],
            y=data['tendencia']['TotalResultados'],
            mode='lines+markers',
            name='Resultados',
            line=dict(color=COLORS['primary'], width=2),
            fill='tozeroy'
        ))
        fig_tend.add_trace(go.Scatter(
            x=data['tendencia']['Fecha'],
            y=data['tendencia']['TotalPacientes'],
            mode='lines+markers',
            name='Pacientes',
            line=dict(color=COLORS['secondary'], width=2),
            yaxis='y2'
        ))
        fig_tend.update_layout(
            height=400,
            hovermode='x unified',
            yaxis=dict(title='Resultados'),
            yaxis2=dict(title='Pacientes', overlaying='y', side='right'),
            legend=dict(orientation='h', y=1.05)
        )
        st.plotly_chart(fig_tend, use_container_width=True)

    render_footer()

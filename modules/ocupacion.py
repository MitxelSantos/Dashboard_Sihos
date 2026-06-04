"""
Módulo Ocupación — Camas reales (Activa=1, Habilita=1)
Excluye 366 camas virtuales (Habilita=0).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.db_connector import get_db_connector
from utils.queries import SIHOSQueries, dataframe_to_excel
from config.settings import COLORS, CACHE_TTL
from components.widgets import render_section_banner, render_section_divider
from components.layout import render_footer


def render_ocupacion():
    """Función principal del módulo de Ocupación."""

    render_section_banner("🛏️", "Ocupación Hospitalaria")
    st.caption(
        "Solo camas reales: Activa=1, Habilita=1 · "
        "Las camas virtuales (Habilita=0) están excluidas del conteo."
    )
    st.info(
        "ℹ️ Las camas bloqueadas (admisión cerrada sin liberar o con egreso sin cerrar) "
        "se analizan en detalle en **Reportes → Camas Bloqueadas**."
    )

    @st.cache_data(ttl=CACHE_TTL)
    def load_ocupacion_data():
        db = get_db_connector()
        queries = SIHOSQueries()
        data = {}
        try:
            data['kpis']    = db.execute_query(queries.get_ocupacion_kpis_real(), {})
            data['serv']    = db.execute_query(queries.get_ocupacion_resumen_servicios(), {})
            data['detalle'] = db.execute_query(queries.get_ocupacion_detalle_camas(), {})
        except Exception as e:
            st.error(f"Error cargando datos de ocupación: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None
        return data

    data = load_ocupacion_data()
    if data is None:
        st.stop()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    if not data['kpis'].empty:
        row = data['kpis'].iloc[0]
        total_reales = int(row.get('total_reales', 0) or 0)
        ocupadas     = int(row.get('ocupadas_reales', 0) or 0)
        libres       = int(row.get('libres', 0) or 0)
        bloqueadas   = int(row.get('bloqueadas', 0) or 0)
        virtuales    = int(row.get('virtuales_excluidas', 0) or 0)
        pct          = round(ocupadas / total_reales * 100, 1) if total_reales > 0 else 0.0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Camas reales",        f"{total_reales:,}")
        k2.metric("Ocupadas",            f"{ocupadas:,}",
                  delta=f"{pct}%")
        k3.metric("Libres",              f"{libres:,}")
        k4.metric("Bloqueadas",          f"{bloqueadas:,}",
                  delta="ver Reportes", delta_color="inverse")
        k5.metric("Virtuales excluidas", f"{virtuales:,}",
                  delta="Habilita=0", delta_color="off")

        # Barra de ocupación visual
        color_barra = "#4CAF50" if pct < 70 else "#FF9800" if pct < 90 else "#F44336"
        st.markdown(f"""
            <div style='margin:8px 0 4px 0; font-size:13px; color:#666'>
                Porcentaje de ocupación real
            </div>
            <div style='background:#E0E0E0; border-radius:8px; height:22px; width:100%'>
                <div style='background:{color_barra}; width:{min(pct, 100)}%;
                            height:22px; border-radius:8px; text-align:center;
                            color:white; font-weight:bold; line-height:22px; font-size:13px'>
                    {pct}%
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("")

    render_section_divider()

    # ── Gráficos ───────────────────────────────────────────────────────────────
    render_section_banner("📊", "Distribución de Ocupación")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Ocupación por servicio")
        if not data['serv'].empty:
            df_serv_graf = data['serv'][data['serv']['camas_reales'] > 0].copy()
            df_serv_graf['pct_ocup'] = (
                df_serv_graf['camas_ocupadas'] / df_serv_graf['camas_reales'] * 100
            ).round(1)
            fig = px.bar(
                df_serv_graf.sort_values('camas_ocupadas', ascending=True),
                x='camas_ocupadas',
                y='CodiServ',
                orientation='h',
                color='pct_ocup',
                color_continuous_scale='RdYlGn_r',
                range_color=[0, 100],
                text='camas_ocupadas',
                labels={
                    'camas_ocupadas': 'Camas ocupadas',
                    'CodiServ':       'Servicio',
                    'pct_ocup':       '% Ocup.',
                },
                height=420,
            )
            fig.update_layout(
                coloraxis_colorbar=dict(title='% Ocup.'),
                yaxis=dict(autorange='reversed'),
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### Distribución de estado de camas")
        if not data['detalle'].empty:
            estado_cnt = data['detalle']['estado'].value_counts().reset_index()
            estado_cnt.columns = ['Estado', 'Cantidad']
            colores_estado = {
                'Libre':                         '#4CAF50',
                'Ocupada':                       '#2196F3',
                'Bloqueada (bug Sinergia)':       '#F44336',
                'Bloqueada (proceso incompleto)': '#FF9800',
                'Estado desconocido':             '#9E9E9E',
            }
            fig2 = px.pie(
                estado_cnt,
                names='Estado',
                values='Cantidad',
                color='Estado',
                color_discrete_map=colores_estado,
                hole=0.45,
            )
            fig2.update_traces(textinfo='percent+label')
            fig2.update_layout(
                showlegend=True,
                height=420,
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Gráfico apilado Libre / Ocupada / Bloqueada por servicio
    if not data['serv'].empty:
        st.markdown("#### 🛏️ Estado de camas por servicio")
        df_stack = data['serv'].copy()
        fig_stack = go.Figure()
        fig_stack.add_trace(go.Bar(
            name='Ocupadas', y=df_stack['CodiServ'], x=df_stack['camas_ocupadas'],
            orientation='h', marker_color='#2196F3',
        ))
        fig_stack.add_trace(go.Bar(
            name='Libres', y=df_stack['CodiServ'], x=df_stack['camas_libres'],
            orientation='h', marker_color='#4CAF50', opacity=0.8,
        ))
        fig_stack.add_trace(go.Bar(
            name='Bloqueadas', y=df_stack['CodiServ'], x=df_stack['camas_bloqueadas'],
            orientation='h', marker_color='#F44336',
        ))
        fig_stack.update_layout(
            barmode='stack',
            height=max(300, len(df_stack) * 35),
            xaxis_title='Camas',
            legend=dict(orientation='h', y=1.05),
            hovermode='y unified',
        )
        st.plotly_chart(fig_stack, use_container_width=True)

    render_section_divider()

    # ── Tabla detalle ──────────────────────────────────────────────────────────
    render_section_banner("📋", "Detalle por Cama")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        servicios = ['Todos'] + sorted(data['detalle']['CodiServ'].dropna().unique().tolist())
        serv_sel  = st.selectbox("Servicio", servicios, key="ocup_serv")
    with col_f2:
        estados   = ['Todos'] + sorted(data['detalle']['estado'].dropna().unique().tolist())
        est_sel   = st.selectbox("Estado", estados, key="ocup_estado")

    df_filt = data['detalle'].copy()
    if serv_sel != 'Todos':
        df_filt = df_filt[df_filt['CodiServ'] == serv_sel]
    if est_sel != 'Todos':
        df_filt = df_filt[df_filt['estado'] == est_sel]

    st.caption(f"Mostrando {len(df_filt):,} de {len(data['detalle']):,} camas reales")
    st.dataframe(df_filt, use_container_width=True, hide_index=True)

    buf = io.BytesIO()
    df_filt.to_excel(buf, index=False, engine='openpyxl')
    buf.seek(0)
    st.download_button(
        "⬇️ Exportar Excel",
        data=buf,
        file_name=f"ocupacion_{serv_sel}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    render_footer()

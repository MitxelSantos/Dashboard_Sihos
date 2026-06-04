import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

EXCEL_PATH = Path("inventario_hospital_v1.xlsx")

# ── Columnas de seguridad (CONF/INT/CRIT) ───────────────────────
CONF_COLS = [c for c in [
    'CONF 1: Información pública', 'CONF 2: Información interna',
    'CONF 3: Datos de identidad', 'CONF 4: Datos de contacto',
    'CONF 5: Información técnica TI', 'CONF 6: Datos personales sensibles',
    'CONF 7: Datos financieros', 'CONF 8: Información secreta',
    'CONF 9: Información confidencial de negocio',
] if True]
INT_COLS  = ['INT 1: Persistencia de información',
             'INT 2: Información en tránsito', 'INT 3: Información en proceso']
CRIT_COLS = ['CRIT 1: Afecta trabajadores', 'CRIT 2: Afecta usuarios externos',
             'CRIT 3: Afecta operación principal', 'CRIT 4: Afecta procesos de apoyo',
             'CRIT 5: Afecta TI/Seguridad', 'CRIT 6: Incumplimiento legal']


@st.cache_data(ttl=300)
def cargar_inventario():
    xl = pd.read_excel(EXCEL_PATH, sheet_name=None)
    return xl


def score_seguridad(row, cols):
    """Cuenta cuántos atributos de seguridad aplican (Sí)."""
    return sum(1 for c in cols if c in row.index and str(row[c]).strip().lower() == 'sí')


def show_inventario():
    st.title("🖥️ Inventario Tecnológico")
    st.caption(f"Fuente: {EXCEL_PATH.name} · Hoja principal: Equipos de Cómputo")

    if not EXCEL_PATH.exists():
        st.error(f"No se encontró el archivo `{EXCEL_PATH}` en la raíz del proyecto.")
        return

    xl = cargar_inventario()
    df = xl.get("Equipos de Cómputo", pd.DataFrame()).copy()

    if df.empty:
        st.warning("La hoja 'Equipos de Cómputo' está vacía.")
        return

    # ── Normalizar columna Área (Vacunación / Vacunacion → Vacunación) ──
    df['Área / Servicio'] = df['Área / Servicio'].str.strip()
    df['Área / Servicio'] = df['Área / Servicio'].replace({'Vacunacion': 'Vacunación'})

    # ── Score de seguridad ───────────────────────────────────────
    df['Score Confidencialidad'] = df.apply(lambda r: score_seguridad(r, CONF_COLS), axis=1)
    df['Score Integridad']       = df.apply(lambda r: score_seguridad(r, INT_COLS),  axis=1)
    df['Score Criticidad']       = df.apply(lambda r: score_seguridad(r, CRIT_COLS), axis=1)
    df['Score Total']            = df['Score Confidencialidad'] + df['Score Integridad'] + df['Score Criticidad']

    # ── Tabs internos ────────────────────────────────────────────
    tab_res, tab_eq, tab_seg, tab_mant, tab_otros = st.tabs([
        "📊 Resumen", "🖥️ Equipos", "🔒 Seguridad", "🔧 Mantenimiento", "📦 Otros activos"
    ])

    # ════════════════════════════════════════════════════════════
    # TAB 1 — RESUMEN EJECUTIVO
    # ════════════════════════════════════════════════════════════
    with tab_res:
        st.subheader("Resumen ejecutivo")

        total    = len(df)
        optimos  = (df['Estado Operativo'].str.contains('Óptimo',  na=False)).sum()
        regulares= (df['Estado Operativo'].str.contains('Regular', na=False)).sum()
        defic    = (df['Estado Operativo'].str.contains('Deficiente', na=False)).sum()
        sin_lic  = (df['Estado Licencia Windows'].isin(['No activado', 'No detectado'])).sum()
        win11    = (df['Sistema Operativo'] == 'Windows 11').sum()
        con_ssd  = (df['Disco 1: Tipo'] == 'SSD').sum()

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total equipos",     total)
        c2.metric("Óptimos",           optimos,   delta=f"{optimos/total*100:.0f}%")
        c3.metric("Regulares",         regulares, delta=f"-{regulares}", delta_color="inverse")
        c4.metric("Sin licencia Win",  sin_lic,   delta=f"{sin_lic/total*100:.0f}%", delta_color="inverse")
        c5.metric("Windows 11",        win11,     delta=f"{win11/total*100:.0f}%")
        c6.metric("Con SSD",           con_ssd,   delta=f"{con_ssd/total*100:.0f}%")

        st.divider()
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown("##### Por tipo de equipo")
            fig = px.pie(df, names='Tipo de Equipo', hole=0.45,
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textinfo='percent+label')
            fig.update_layout(showlegend=False, height=260, margin=dict(t=10,b=10,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("##### Por estado operativo")
            estado_colors = {
                'Operativo - Óptimo':      '#4CAF50',
                'Operativo - Regular':     '#FF9800',
                'Operativo - Deficiente':  '#F44336',
            }
            cnt = df['Estado Operativo'].value_counts().reset_index()
            cnt.columns = ['Estado', 'Cantidad']
            cnt['Color'] = cnt['Estado'].map(estado_colors)
            fig2 = px.bar(cnt, x='Estado', y='Cantidad',
                          color='Estado',
                          color_discrete_map=estado_colors,
                          text='Cantidad')
            fig2.update_layout(showlegend=False, height=260,
                               margin=dict(t=10,b=10), xaxis_title='',
                               xaxis_tickangle=-20)
            fig2.update_traces(textposition='outside')
            st.plotly_chart(fig2, use_container_width=True)

        with col_c:
            st.markdown("##### Por área / servicio")
            area_cnt = df['Área / Servicio'].value_counts().reset_index()
            area_cnt.columns = ['Área', 'Cantidad']
            fig3 = px.bar(area_cnt, x='Cantidad', y='Área', orientation='h',
                          color='Cantidad', color_continuous_scale='Blues')
            fig3.update_layout(showlegend=False, height=260,
                               margin=dict(t=10,b=10), yaxis=dict(autorange='reversed'),
                               coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)

        st.divider()
        col_d, col_e = st.columns(2)

        with col_d:
            st.markdown("##### Sistema Operativo & RAM")
            fig4 = px.histogram(df, x='RAM (GB)', color='Sistema Operativo',
                                barmode='group',
                                color_discrete_map={'Windows 10': '#0078D7', 'Windows 11': '#00B294'})
            fig4.update_layout(height=280, margin=dict(t=10,b=10))
            st.plotly_chart(fig4, use_container_width=True)

        with col_e:
            st.markdown("##### Licencia Windows")
            lic_cnt = df['Estado Licencia Windows'].value_counts().reset_index()
            lic_cnt.columns = ['Estado', 'Cantidad']
            lic_colors = {'Activado': '#4CAF50', 'No activado': '#F44336', 'No detectado': '#9E9E9E'}
            fig5 = px.pie(lic_cnt, names='Estado', values='Cantidad', hole=0.5,
                          color='Estado', color_discrete_map=lic_colors)
            fig5.update_traces(textinfo='percent+label')
            fig5.update_layout(showlegend=False, height=280, margin=dict(t=10,b=10,l=10,r=10))
            st.plotly_chart(fig5, use_container_width=True)

    # ════════════════════════════════════════════════════════════
    # TAB 2 — TABLA DE EQUIPOS
    # ════════════════════════════════════════════════════════════
    with tab_eq:
        st.subheader("Inventario de equipos de cómputo")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            areas = ['Todas'] + sorted(df['Área / Servicio'].dropna().unique().tolist())
            area_sel = st.selectbox("Área / Servicio", areas)
        with col_f2:
            estados = ['Todos'] + sorted(df['Estado Operativo'].dropna().unique().tolist())
            estado_sel = st.selectbox("Estado", estados)
        with col_f3:
            tipos = ['Todos'] + sorted(df['Tipo de Equipo'].dropna().unique().tolist())
            tipo_sel = st.selectbox("Tipo de equipo", tipos)

        df_filt = df.copy()
        if area_sel   != 'Todas': df_filt = df_filt[df_filt['Área / Servicio'] == area_sel]
        if estado_sel != 'Todos': df_filt = df_filt[df_filt['Estado Operativo'] == estado_sel]
        if tipo_sel   != 'Todos': df_filt = df_filt[df_filt['Tipo de Equipo']   == tipo_sel]

        st.caption(f"Mostrando {len(df_filt)} de {total} equipos")

        cols_tabla = ['Código', 'Nombre Equipo', 'Tipo de Equipo', 'Área / Servicio',
                      'Estado Operativo', 'Marca', 'Modelo', 'Sistema Operativo',
                      'RAM (GB)', 'Disco 1: Tipo', 'Disco 1: Capacidad (GB)',
                      'Estado Licencia Windows', 'Estado Antivirus',
                      'Dirección IP', 'ID AnyDesk', 'Uso SIHOS',
                      'Observaciones Técnicas']
        cols_tabla = [c for c in cols_tabla if c in df_filt.columns]

        st.dataframe(df_filt[cols_tabla], use_container_width=True, hide_index=True)

        # Alertas
        sin_ip  = df_filt[df_filt['Dirección IP'].isna() |
                          (df_filt['Dirección IP'].astype(str).str.strip() == '')].shape[0]
        sin_any = df_filt[df_filt['ID AnyDesk'].isna() |
                          (df_filt['ID AnyDesk'].astype(str).isin(['No instalado','nan','',' ']))].shape[0]
        obs     = df_filt[df_filt['Observaciones Técnicas'].notna() &
                          (df_filt['Observaciones Técnicas'].astype(str).str.strip() != '')].shape[0]

        ca, cb, cc = st.columns(3)
        ca.metric("Sin IP registrada",    sin_ip)
        cb.metric("Sin AnyDesk",          sin_any)
        cc.metric("Con observación técnica", obs)

        # Descarga
        import io
        buf = io.BytesIO()
        df_filt[cols_tabla].to_excel(buf, index=False, engine='openpyxl')
        buf.seek(0)
        st.download_button("⬇️ Exportar vista actual",
                           data=buf,
                           file_name=f"inventario_filtrado_{area_sel}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ════════════════════════════════════════════════════════════
    # TAB 3 — SEGURIDAD
    # ════════════════════════════════════════════════════════════
    with tab_seg:
        st.subheader("Clasificación de seguridad de la información")
        st.caption("Basado en atributos CONF (Confidencialidad), INT (Integridad), CRIT (Criticidad)")

        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("##### Score de criticidad por área")
            area_score = df.groupby('Área / Servicio')[['Score Confidencialidad',
                                                         'Score Integridad',
                                                         'Score Criticidad']].mean().round(1).reset_index()
            area_score = area_score.sort_values('Score Criticidad', ascending=False)
            fig_sc = px.bar(area_score, x='Score Criticidad', y='Área / Servicio',
                            orientation='h', color='Score Confidencialidad',
                            color_continuous_scale='RdYlGn_r',
                            labels={'Score Criticidad': 'Criticidad promedio'})
            fig_sc.update_layout(height=380, margin=dict(t=10,b=10),
                                  yaxis=dict(autorange='reversed'))
            st.plotly_chart(fig_sc, use_container_width=True)

        with col_s2:
            st.markdown("##### Top equipos por score total de riesgo")
            top_risk = df[['Código','Nombre Equipo','Área / Servicio',
                           'Score Total','Score Criticidad','Score Confidencialidad']]\
                         .sort_values('Score Total', ascending=False).head(10)
            st.dataframe(top_risk, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("##### Mapa de calor: atributos de seguridad por equipo")
        heatmap_cols = CONF_COLS + INT_COLS + CRIT_COLS
        heatmap_cols = [c for c in heatmap_cols if c in df.columns]
        df_heat = df[['Código'] + heatmap_cols].set_index('Código')
        df_heat_num = df_heat.apply(
            lambda col: col.map(lambda v: 1 if str(v).strip().lower() == 'sí' else 0)
        )
        short_labels = (
            [f"C{i+1}" for i in range(len(CONF_COLS))] +
            [f"I{i+1}" for i in range(len(INT_COLS))] +
            [f"CR{i+1}" for i in range(len(CRIT_COLS))]
        )
        short_labels = short_labels[:len(df_heat_num.columns)]
        fig_heat = px.imshow(df_heat_num.T,
                             x=df_heat_num.index,
                             y=short_labels,
                             color_continuous_scale=[[0,'#ECEFF1'],[1,'#1565C0']],
                             aspect='auto')
        fig_heat.update_layout(height=380, margin=dict(t=10,b=10),
                                xaxis_title='Equipo', yaxis_title='Atributo')
        st.plotly_chart(fig_heat, use_container_width=True)
        st.caption("C=Confidencialidad, I=Integridad, CR=Criticidad · Azul=Aplica, Gris=No aplica")

    # ════════════════════════════════════════════════════════════
    # TAB 4 — MANTENIMIENTO
    # ════════════════════════════════════════════════════════════
    with tab_mant:
        st.subheader("Historial de mantenimientos")

        df_mant = xl.get("Mantenimientos", pd.DataFrame()).copy()

        if df_mant.empty or len(df_mant) == 0:
            st.info("Aún no hay registros de mantenimiento en la hoja 'Mantenimientos'.")
        else:
            st.dataframe(df_mant, use_container_width=True, hide_index=True)

            if 'Tipo Mantenimiento' in df_mant.columns:
                cnt_tipo = df_mant['Tipo Mantenimiento'].value_counts().reset_index()
                cnt_tipo.columns = ['Tipo', 'Cantidad']
                fig_m = px.pie(cnt_tipo, names='Tipo', values='Cantidad', hole=0.4,
                               title='Distribución por tipo de mantenimiento')
                fig_m.update_layout(height=300)
                st.plotly_chart(fig_m, use_container_width=True)

        st.divider()
        st.markdown("##### Equipos por periodicidad de mantenimiento")
        per_cnt = df['Periodicidad Mantenimiento'].value_counts().reset_index()
        per_cnt.columns = ['Periodicidad', 'Equipos']
        fig_per = px.bar(per_cnt, x='Periodicidad', y='Equipos', text='Equipos',
                         color='Equipos', color_continuous_scale='Blues')
        fig_per.update_layout(height=280, margin=dict(t=10,b=10),
                               coloraxis_showscale=False)
        fig_per.update_traces(textposition='outside')
        st.plotly_chart(fig_per, use_container_width=True)

    # ════════════════════════════════════════════════════════════
    # TAB 5 — OTROS ACTIVOS
    # ════════════════════════════════════════════════════════════
    with tab_otros:
        st.subheader("Otros activos tecnológicos")

        sub1, sub2, sub3, sub4 = st.tabs(
            ["🖨️ Impresoras y Escáneres", "🖱️ Periféricos", "🌐 Red", "⚰️ Dados de Baja"]
        )

        with sub1:
            df_imp = xl.get("Impresoras y Escáneres", pd.DataFrame())
            st.metric("Total registros", len(df_imp))
            st.dataframe(df_imp, use_container_width=True, hide_index=True)

        with sub2:
            df_per = xl.get("Periféricos", pd.DataFrame())
            st.metric("Total registros", len(df_per))
            st.dataframe(df_per, use_container_width=True, hide_index=True)

        with sub3:
            df_red = xl.get("Equipos de Red", pd.DataFrame())
            st.metric("Total registros", len(df_red))
            st.dataframe(df_red, use_container_width=True, hide_index=True)

        with sub4:
            df_baja = xl.get("Equipos Dados de Baja", pd.DataFrame())
            st.metric("Total equipos dados de baja", len(df_baja))
            st.dataframe(df_baja, use_container_width=True, hide_index=True)

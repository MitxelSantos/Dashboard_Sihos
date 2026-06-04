# SIHOS_Parte11_Ocupacion.md
## Instrucción para Claude Code en VS Code

Lee este archivo completo y aplica TODOS los cambios en orden.

---

## RESUMEN DE CAMBIOS

| # | Archivo | Qué cambia |
|---|---------|------------|
| A | `modules/consultas_sql.py` | Fix bug `selector_sql` session_state |
| B | `db/queries.py` | Queries de ocupación corregidas con `Activa=1 AND Habilita=1` |
| C | `modules/ocupacion.py` | Refactor completo con camas reales vs virtuales |

---

## CAMBIO A — `modules/consultas_sql.py`: Fix session_state

Localiza la función principal del módulo (probablemente `show_consultas_sql()`).
Al inicio del cuerpo de esa función, **antes de cualquier uso de `st.session_state`**,
agrega las siguientes líneas de inicialización:

```python
# Inicializar session_state para evitar AttributeError
if 'selector_sql' not in st.session_state:
    st.session_state['selector_sql'] = ''
if 'query_sql' not in st.session_state:
    st.session_state['query_sql'] = ''
if 'resultado_sql' not in st.session_state:
    st.session_state['resultado_sql'] = None
```

---

## CAMBIO B — `db/queries.py`: Queries de ocupación corregidas

Localiza las funciones de ocupación existentes y **reemplázalas** con las siguientes
(si no existen, agrégalas al final del archivo):

```python
# ─── OCUPACIÓN ────────────────────────────────────────────────────────────────

def get_ocupacion_resumen(conn) -> pd.DataFrame:
    """
    Resumen de ocupación por servicio.
    - Denominador: camas REALES (Activa=1, Habilita=1) — excluye virtuales
    - Numerador: camas con ConsAdmi apuntando a admisión activa legítima
      (Cerrado=2, Anulado=2, FechEgre IS NULL)
    """
    query = """
        SELECT
            cc.CodiServ,
            COUNT(cc.CodiCama)                                      AS camas_reales,
            SUM(CASE
                WHEN a.ConsAdmi IS NOT NULL
                     AND a.Cerrado = 2
                     AND a.Anulado = 2
                     AND a.FechEgre IS NULL
                THEN 1 ELSE 0
            END)                                                    AS camas_ocupadas,
            SUM(CASE
                WHEN cc.ConsAdmi IS NULL OR cc.ConsAdmi = ''
                THEN 1 ELSE 0
            END)                                                    AS camas_libres,
            SUM(CASE
                WHEN cc.ConsAdmi IS NOT NULL
                     AND cc.ConsAdmi != ''
                     AND (a.ConsAdmi IS NULL
                          OR a.Cerrado != 2
                          OR a.Anulado != 2
                          OR a.FechEgre IS NOT NULL)
                THEN 1 ELSE 0
            END)                                                    AS camas_bloqueadas
        FROM CodiCama cc
        LEFT JOIN Admision a ON cc.ConsAdmi = a.ConsAdmi
        WHERE cc.Activa = 1
          AND cc.Habilita = 1
        GROUP BY cc.CodiServ
        ORDER BY camas_ocupadas DESC
    """
    return pd.read_sql(query, conn)


def get_ocupacion_kpis(conn) -> dict:
    """KPIs globales de ocupación con camas reales únicamente."""
    query = """
        SELECT
            COUNT(cc.CodiCama)                                      AS total_reales,
            SUM(CASE
                WHEN a.ConsAdmi IS NOT NULL
                     AND a.Cerrado = 2
                     AND a.Anulado = 2
                     AND a.FechEgre IS NULL
                THEN 1 ELSE 0
            END)                                                    AS ocupadas_reales,
            SUM(CASE
                WHEN cc.ConsAdmi IS NULL OR cc.ConsAdmi = ''
                THEN 1 ELSE 0
            END)                                                    AS libres,
            SUM(CASE
                WHEN cc.ConsAdmi IS NOT NULL
                     AND cc.ConsAdmi != ''
                     AND (a.ConsAdmi IS NULL
                          OR a.Cerrado != 2
                          OR a.Anulado != 2
                          OR a.FechEgre IS NOT NULL)
                THEN 1 ELSE 0
            END)                                                    AS bloqueadas,
            (SELECT COUNT(*) FROM CodiCama
             WHERE Activa = 1 AND Habilita = 0)                     AS virtuales_excluidas
        FROM CodiCama cc
        LEFT JOIN Admision a ON cc.ConsAdmi = a.ConsAdmi
        WHERE cc.Activa = 1
          AND cc.Habilita = 1
    """
    df = pd.read_sql(query, conn)
    row = df.iloc[0]
    total = int(row['total_reales'] or 0)
    ocup  = int(row['ocupadas_reales'] or 0)
    return {
        'total_reales':       total,
        'ocupadas_reales':    ocup,
        'libres':             int(row['libres'] or 0),
        'bloqueadas':         int(row['bloqueadas'] or 0),
        'virtuales_excluidas':int(row['virtuales_excluidas'] or 0),
        'porcentaje_ocup':    round(ocup / total * 100, 1) if total > 0 else 0.0,
    }


def get_ocupacion_detalle_camas(conn) -> pd.DataFrame:
    """Detalle de cada cama real con su estado actual."""
    query = """
        SELECT
            cc.CodiCama,
            cc.NombCama,
            cc.CodiServ,
            CASE
                WHEN cc.ConsAdmi IS NULL OR cc.ConsAdmi = ''
                    THEN 'Libre'
                WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL
                    THEN 'Ocupada'
                WHEN a.Cerrado = 1
                    THEN 'Bloqueada (bug Sinergia)'
                WHEN a.FechEgre IS NOT NULL AND a.Cerrado = 2
                    THEN 'Bloqueada (proceso incompleto)'
                ELSE 'Estado desconocido'
            END                                                 AS estado,
            cc.ConsAdmi,
            a.FechIngr,
            a.FechEgre,
            CASE
                WHEN a.FechIngr IS NOT NULL
                THEN DATEDIFF(CURDATE(), a.FechIngr)
            END                                                 AS dias_ocupada,
            a.UsuaModi                                          AS responsable
        FROM CodiCama cc
        LEFT JOIN Admision a ON cc.ConsAdmi = a.ConsAdmi
        WHERE cc.Activa = 1
          AND cc.Habilita = 1
        ORDER BY cc.CodiServ, estado, cc.CodiCama
    """
    return pd.read_sql(query, conn)
```

---

## CAMBIO C — `modules/ocupacion.py`: Refactor completo

Reemplaza el contenido de la función principal `show_ocupacion()` con el siguiente código:

```python
def show_ocupacion():
    st.title("🛏️ Ocupación Hospitalaria")
    st.caption(
        "Solo camas reales: Activa=1, Habilita=1 · "
        "Las 366 camas virtuales (Habilita=0) están excluidas del conteo"
    )

    with st.spinner("Cargando ocupación..."):
        try:
            kpis      = get_ocupacion_kpis(conn)
            df_serv   = get_ocupacion_resumen(conn)
            df_det    = get_ocupacion_detalle_camas(conn)
            ocup_ok   = True
        except Exception as e:
            st.error(f"Error cargando ocupación: {e}")
            ocup_ok = False

    if not ocup_ok:
        return

    # ── KPIs ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Camas reales",          f"{kpis['total_reales']:,}")
    k2.metric("Ocupadas",              f"{kpis['ocupadas_reales']:,}",
              delta=f"{kpis['porcentaje_ocup']}%")
    k3.metric("Libres",                f"{kpis['libres']:,}")
    k4.metric("Bloqueadas",            f"{kpis['bloqueadas']:,}",
              delta="ver Reportes", delta_color="inverse")
    k5.metric("Virtuales excluidas",   f"{kpis['virtuales_excluidas']:,}",
              delta="Habilita=0", delta_color="off")

    # Barra de ocupación visual
    pct = kpis['porcentaje_ocup']
    color = "#4CAF50" if pct < 70 else "#FF9800" if pct < 90 else "#F44336"
    st.markdown(f"""
        <div style='margin:8px 0 4px 0; font-size:13px; color:#666'>
            Porcentaje de ocupación real
        </div>
        <div style='background:#E0E0E0; border-radius:8px; height:22px; width:100%'>
            <div style='background:{color}; width:{min(pct,100)}%;
                        height:22px; border-radius:8px; text-align:center;
                        color:white; font-weight:bold; line-height:22px; font-size:13px'>
                {pct}%
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    st.divider()

    # ── Gráficos ──────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Ocupación por servicio")
        if not df_serv.empty:
            import plotly.express as px
            df_serv_graf = df_serv[df_serv['camas_reales'] > 0].copy()
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
        if not df_det.empty:
            import plotly.express as px
            estado_cnt = df_det['estado'].value_counts().reset_index()
            estado_cnt.columns = ['Estado', 'Cantidad']
            colores_estado = {
                'Libre':                          '#4CAF50',
                'Ocupada':                        '#2196F3',
                'Bloqueada (bug Sinergia)':        '#F44336',
                'Bloqueada (proceso incompleto)':  '#FF9800',
                'Estado desconocido':              '#9E9E9E',
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

    st.divider()

    # ── Tabla detalle ─────────────────────────────────────────────────────
    st.markdown("#### Detalle por cama")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        servicios = ['Todos'] + sorted(df_det['CodiServ'].dropna().unique().tolist())
        serv_sel  = st.selectbox("Servicio", servicios, key="ocup_serv")
    with col_f2:
        estados   = ['Todos'] + sorted(df_det['estado'].dropna().unique().tolist())
        est_sel   = st.selectbox("Estado", estados, key="ocup_estado")

    df_filt = df_det.copy()
    if serv_sel != 'Todos':
        df_filt = df_filt[df_filt['CodiServ'] == serv_sel]
    if est_sel != 'Todos':
        df_filt = df_filt[df_filt['estado'] == est_sel]

    st.caption(f"Mostrando {len(df_filt):,} de {len(df_det):,} camas reales")
    st.dataframe(df_filt, use_container_width=True, hide_index=True)

    # Descarga
    import io
    buf = io.BytesIO()
    df_filt.to_excel(buf, index=False, engine='openpyxl')
    buf.seek(0)
    st.download_button(
        "⬇️ Exportar Excel",
        data=buf,
        file_name=f"ocupacion_{serv_sel}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
```

---

## CAMBIO D — `modules/ocupacion.py`: Verificar imports

Al inicio de `modules/ocupacion.py`, asegúrate de que existan estos imports:

```python
import streamlit as st
import pandas as pd
import plotly.express as px
import io
from db.queries import (
    get_ocupacion_kpis,
    get_ocupacion_resumen,
    get_ocupacion_detalle_camas,
    # ... otros imports existentes ...
)
```

---

## NOTAS TÉCNICAS

1. **Camas virtuales confirmadas**: 366 camas con `Activa=1, Habilita=0` — encabezadas por
   servicio 38 "Cama virtual X" (120 camas). Completamente excluidas del denominador.

2. **Camas reales confirmadas**: 611 (`Activa=1, Habilita=1`) distribuidas en 12 servicios.
   Servicio 9 (168), Servicio 8 (151) y Servicio 27 (96) son los más grandes.

3. **Tres estados posibles de una cama real**:
   - `Libre`: `ConsAdmi` vacío
   - `Ocupada`: admisión activa (Cerrado=2, Anulado=2, FechEgre IS NULL)
   - `Bloqueada`: `ConsAdmi` apunta a admisión cerrada/con egreso → ver Reportes → Camas Bloqueadas

4. **El porcentaje de ocupación** es sobre camas reales únicamente.
   La barra cambia de color: verde (<70%), naranja (70-90%), rojo (>90%).

5. **`conn`**: si en `modules/ocupacion.py` la conexión se recibe como parámetro
   (ej: `show_ocupacion(conn)`), mantener ese patrón. Si se obtiene dentro del módulo,
   mantener el patrón existente.

---

## VALIDACIÓN ESPERADA

- KPI "Camas reales": 611
- KPI "Virtuales excluidas": 366
- Barra de ocupación: entre 40-60% (ocupadas reales vs 611 totales)
- Donut: 4 segmentos — Libre, Ocupada, Bloqueada bug Sinergia, Bloqueada proceso incompleto
- Tabla filtrable con exactamente 611 filas en total

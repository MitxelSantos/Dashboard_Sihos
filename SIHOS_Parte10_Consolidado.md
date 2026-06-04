# SIHOS_Parte10_Consolidado.md
## Instrucción para Claude Code en VS Code

Lee este archivo completo y aplica TODOS los cambios en orden. Son 6 cambios independientes.

---

## RESUMEN DE CAMBIOS

| # | Archivo | Qué cambia |
|---|---------|------------|
| A | `modules/admisiones.py` | Eliminar sección "Admisiones Abiertas con Cama Asignada" |
| B | `modules/ocupacion.py` | Depurar — solo camas reales activas, sin bloqueos |
| C | `modules/reportes.py` | Aplanar tabs a una sola fila (eliminar "Otros reportes") |
| D | `modules/reportes.py` | Agregar tab "Admisiones sin Cerrar" |
| E | `modules/reportes.py` | Agregar tab "Camas Bloqueadas" |
| F | `modules/reportes.py` | Agregar tab "Usuarios SIHOS" |

---

## CAMBIO A — `modules/admisiones.py`: Eliminar módulo de admisiones abiertas

En `modules/admisiones.py`, localiza y **elimina completamente** la sección que muestra admisiones abiertas con cama asignada. Esta sección probablemente incluye:
- Un subheader como "Admisiones Abiertas con Cama Asignada" o similar
- KPIs de total abiertas, días promedio, máx días, hospitalizadas
- Gráficos por servicio y distribución por antigüedad
- Un expander con tabla detallada

Reemplaza todo ese bloque con un comentario:
```python
# Módulo "Admisiones Abiertas" movido a Reportes → tab "Admisiones sin Cerrar"
```

La pestaña Admisiones queda exclusivamente con análisis de flujo por período (ingresos, egresos, tendencia, distribución por tipo/servicio/diagnóstico).

---

## CAMBIO B — `modules/ocupacion.py`: Depurar ocupación real

En `modules/ocupacion.py`, la query principal de ocupación debe mostrar **solo pacientes activos legítimos** (sin FechEgre, Cerrado=2). Si actualmente usa `CodiCama.ConsAdmi` para contar ocupación, reemplazar por la query correcta:

```python
# Query de ocupación real — pacientes presentes sin egreso registrado
QUERY_OCUPACION_REAL = """
    SELECT 
        cs.CodiServ,
        COUNT(*) AS camas_ocupadas_reales
    FROM CodiCama cc
    JOIN Admision a ON cc.ConsAdmi = a.ConsAdmi
    WHERE a.Cerrado = 2
      AND a.Anulado = 2
      AND a.FechEgre IS NULL
      AND DATEDIFF(CURDATE(), a.FechIngr) <= 60
    GROUP BY cs.CodiServ
"""
```

Agregar una nota informativa visible en la pestaña:
```python
st.info(
    "ℹ️ La ocupación muestra únicamente pacientes con admisión activa y sin egreso registrado "
    "(≤60 días). Las admisiones con proceso incompleto o bug de sistema se analizan en "
    "**Reportes → Camas Bloqueadas**."
)
```

---

## CAMBIO C — `modules/reportes.py`: Aplanar pestañas a una sola fila

### Estructura actual (dos niveles):
```python
tab_rda, tab_373, tab_otros = st.tabs([...])
with tab_otros:
    tab_cierres, tab_rips, tab_373exp, tab_sismed = st.tabs([...])
```

### Estructura nueva (un solo nivel con 9 tabs):
```python
(tab_rda, tab_373, tab_cierres, tab_sin_cerrar,
 tab_camas, tab_usuarios, tab_rips, tab_373exp, tab_sismed) = st.tabs([
    "🔗 Interoperabilidad RDA",
    "🚨 Resolución 373",
    "🔍 Auditoría Cierres",
    "📂 Admisiones sin Cerrar",
    "🛏️ Camas Bloqueadas",
    "👥 Usuarios SIHOS",
    "📄 RIPS",
    "📋 Res. 373 (export)",
    "🚀 SISMED",
])
```

Mueve el contenido de cada sub-tab existente a su tab directo. Los tabs nuevos (`tab_sin_cerrar`, `tab_camas`, `tab_usuarios`) se implementan en los cambios D, E y F. Por ahora ponles un placeholder:

```python
with tab_sin_cerrar:
    pass  # implementado en Cambio D

with tab_camas:
    pass  # implementado en Cambio E

with tab_usuarios:
    pass  # implementado en Cambio F
```

---

## CAMBIO D — `modules/reportes.py`: Tab "Admisiones sin Cerrar"

Reemplaza el `pass` del `tab_sin_cerrar` con el siguiente código completo:

### Queries a agregar en `db/queries.py`:

```python
# ─── ADMISIONES SIN CERRAR ────────────────────────────────────────────────────

def get_admisiones_sin_cerrar_resumen(conn) -> pd.DataFrame:
    """Distribución de admisiones sin cerrar por antigüedad."""
    query = """
        SELECT 
            CASE 
                WHEN DATEDIFF(CURDATE(), FechIngr) = 0          THEN '0. Hoy'
                WHEN DATEDIFF(CURDATE(), FechIngr) BETWEEN 1 AND 2   THEN '1. 1-2 días'
                WHEN DATEDIFF(CURDATE(), FechIngr) BETWEEN 3 AND 7   THEN '2. 3-7 días'
                WHEN DATEDIFF(CURDATE(), FechIngr) BETWEEN 8 AND 30  THEN '3. 8-30 días'
                WHEN DATEDIFF(CURDATE(), FechIngr) BETWEEN 31 AND 90 THEN '4. 31-90 días'
                WHEN DATEDIFF(CURDATE(), FechIngr) BETWEEN 91 AND 365 THEN '5. 91-365 días'
                ELSE '6. Más de 1 año'
            END AS rango,
            COUNT(*) AS total,
            AVG(DATEDIFF(CURDATE(), FechIngr)) AS dias_promedio
        FROM Admision
        WHERE Cerrado = 2
          AND Anulado = 2
          AND FechEgre IS NULL
        GROUP BY rango
        ORDER BY rango
    """
    return pd.read_sql(query, conn)


def get_admisiones_sin_cerrar_detalle(conn, dias_minimo: int = 30,
                                       tipo_aten: int = None,
                                       limit: int = 500) -> pd.DataFrame:
    """Detalle de admisiones sin cerrar filtradas por antigüedad mínima."""
    filtro_tipo = f"AND a.TipoAten = {tipo_aten}" if tipo_aten else ""
    query = f"""
        SELECT
            a.ConsAdmi,
            a.FechIngr,
            DATEDIFF(CURDATE(), a.FechIngr)  AS dias_abierta,
            CASE a.TipoAten
                WHEN 1 THEN 'Consulta Externa'
                WHEN 2 THEN 'Hospitalización'
                WHEN 3 THEN 'Urgencias'
                WHEN 4 THEN 'PyP'
                ELSE CONCAT('Tipo ', a.TipoAten)
            END AS tipo_atencion,
            a.CodiServ,
            a.UsuaDigi                       AS usuario_apertura,
            a.UsuaModi                       AS usuario_modifico
        FROM Admision a
        WHERE a.Cerrado = 2
          AND a.Anulado = 2
          AND a.FechEgre IS NULL
          AND DATEDIFF(CURDATE(), a.FechIngr) >= %s
          {filtro_tipo}
        ORDER BY dias_abierta DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, conn, params=[dias_minimo])
```

### Código del tab en `modules/reportes.py`:

```python
with tab_sin_cerrar:
    st.subheader("📂 Admisiones sin Cerrar")
    st.caption(
        "Admisiones con Cerrado=2, Anulado=2 y FechEgre IS NULL — "
        "el sistema las considera activas pero muchas corresponden a "
        "atenciones finalizadas no cerradas formalmente."
    )
    st.warning(
        "⚠️ **Total estimado: ~21,554 admisiones sin cerrar** (dato de auditoría mayo 2026). "
        "Solo 605 son de hoy o ayer — el 87% llevan más de 30 días. "
        "Las ambulatorias (TipoAten=1,4) no bloquean camas pero afectan RIPS y estadísticas."
    )

    with st.spinner("Cargando distribución..."):
        try:
            df_rango = get_admisiones_sin_cerrar_resumen(conn)
            asc_ok = True
        except Exception as e:
            st.error(f"Error: {e}")
            asc_ok = False

    if asc_ok and not df_rango.empty:
        # ── KPIs ─────────────────────────────────────────────────────
        total_asc = int(df_rango['total'].sum())
        legitimas = int(df_rango[df_rango['rango'].isin(['0. Hoy','1. 1-2 días'])]['total'].sum())
        sospechosas = total_asc - legitimas

        k1, k2, k3 = st.columns(3)
        k1.metric("Total sin cerrar",     f"{total_asc:,}")
        k2.metric("Posiblemente activas", f"{legitimas:,}",
                  delta="≤2 días", delta_color="normal")
        k3.metric("Probables errores",    f"{sospechosas:,}",
                  delta=">2 días", delta_color="inverse")

        st.divider()

        # ── Gráfico semáforo ──────────────────────────────────────────
        st.markdown("#### Distribución por antigüedad")
        colores = {
            '0. Hoy':           '#4CAF50',
            '1. 1-2 días':      '#8BC34A',
            '2. 3-7 días':      '#FFC107',
            '3. 8-30 días':     '#FF9800',
            '4. 31-90 días':    '#F44336',
            '5. 91-365 días':   '#B71C1C',
            '6. Más de 1 año':  '#4A148C',
        }
        import plotly.express as px
        df_rango['color'] = df_rango['rango'].map(colores)
        fig_asc = px.bar(
            df_rango, x='rango', y='total',
            color='rango',
            color_discrete_map=colores,
            text='total',
            labels={'rango': 'Antigüedad', 'total': 'Admisiones'},
            height=350,
        )
        fig_asc.update_layout(showlegend=False, xaxis_title='', yaxis_title='Admisiones')
        fig_asc.update_traces(textposition='outside')
        st.plotly_chart(fig_asc, use_container_width=True)

        st.divider()

        # ── Detalle filtrable ─────────────────────────────────────────
        st.markdown("#### Detalle — admisiones problemáticas")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            dias_min = st.slider("Días mínimos abierta", 0, 365, 30, step=1,
                                 key="asc_dias")
        with col_f2:
            tipo_opts = {
                'Todos': None,
                'Consulta Externa (1)': 1,
                'Hospitalización (2)': 2,
                'Urgencias (3)': 3,
                'PyP (4)': 4,
            }
            tipo_sel = st.selectbox("Tipo de atención", list(tipo_opts.keys()),
                                    key="asc_tipo")

        with st.spinner("Cargando detalle..."):
            try:
                df_det = get_admisiones_sin_cerrar_detalle(
                    conn, dias_minimo=dias_min,
                    tipo_aten=tipo_opts[tipo_sel]
                )
            except Exception as e:
                df_det = pd.DataFrame()
                st.error(f"Error cargando detalle: {e}")

        if not df_det.empty:
            st.caption(f"Mostrando {len(df_det):,} admisiones (máx 500) con ≥{dias_min} días")
            st.dataframe(df_det, use_container_width=True, hide_index=True)

            import io
            buf = io.BytesIO()
            df_det.to_excel(buf, index=False, engine='openpyxl')
            buf.seek(0)
            st.download_button(
                "⬇️ Descargar Excel",
                data=buf,
                file_name=f"admisiones_sin_cerrar_{dias_min}d.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
```

---

## CAMBIO E — `modules/reportes.py`: Tab "Camas Bloqueadas"

### Queries a agregar en `db/queries.py`:

```python
# ─── CAMAS BLOQUEADAS ─────────────────────────────────────────────────────────

def get_camas_bug_sinergia(conn) -> pd.DataFrame:
    """Camas con admisión CERRADA o ANULADA que no se liberaron (bug Sinergia)."""
    query = """
        SELECT
            cc.CodiCama,
            cc.NombCama,
            cc.CodiServ,
            cc.ConsAdmi,
            CASE
                WHEN a.Cerrado = 1 AND a.Anulado = 2 THEN 'CERRADA'
                WHEN a.Cerrado = 1 AND a.Anulado = 1 THEN 'ANULADA'
                ELSE 'OTRO'
            END AS tipo_bug,
            a.FechIngr,
            a.FechEgre,
            a.UsuaModi                         AS cerro,
            DATEDIFF(CURDATE(), a.FechIngr)    AS dias_bloqueada
        FROM CodiCama cc
        JOIN Admision a ON cc.ConsAdmi = a.ConsAdmi
        WHERE cc.ConsAdmi IS NOT NULL
          AND cc.ConsAdmi != ''
          AND a.Cerrado = 1
        ORDER BY dias_bloqueada DESC
    """
    return pd.read_sql(query, conn)


def get_camas_proceso_incompleto(conn) -> pd.DataFrame:
    """Camas con FechEgre registrado pero admisión aún abierta (Cerrado=2)."""
    query = """
        SELECT
            cc.CodiCama,
            cc.NombCama,
            cc.CodiServ,
            cc.ConsAdmi,
            a.FechIngr,
            a.FechEgre,
            DATEDIFF(CURDATE(), a.FechIngr)    AS dias_abierta,
            DATEDIFF(CURDATE(), a.FechEgre)    AS dias_desde_egreso,
            a.UsuaModi                         AS responsable
        FROM CodiCama cc
        JOIN Admision a ON cc.ConsAdmi = a.ConsAdmi
        WHERE cc.ConsAdmi IS NOT NULL
          AND cc.ConsAdmi != ''
          AND a.Cerrado = 2
          AND a.Anulado = 2
          AND a.FechEgre IS NOT NULL
          AND a.FechEgre != '0000-00-00'
        ORDER BY dias_desde_egreso DESC
    """
    return pd.read_sql(query, conn)


def get_camas_resumen_por_servicio(conn) -> pd.DataFrame:
    """Resumen de bloqueos por servicio."""
    query = """
        SELECT
            cc.CodiServ,
            SUM(CASE WHEN a.Cerrado = 1 THEN 1 ELSE 0 END)           AS bug_sinergia,
            SUM(CASE WHEN a.Cerrado = 2 AND a.FechEgre IS NOT NULL
                          AND a.FechEgre != '0000-00-00'
                     THEN 1 ELSE 0 END)                               AS proceso_incompleto,
            COUNT(*)                                                   AS total_bloqueadas
        FROM CodiCama cc
        JOIN Admision a ON cc.ConsAdmi = a.ConsAdmi
        WHERE cc.ConsAdmi IS NOT NULL AND cc.ConsAdmi != ''
          AND NOT (a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL)
        GROUP BY cc.CodiServ
        ORDER BY total_bloqueadas DESC
    """
    return pd.read_sql(query, conn)
```

### Código del tab en `modules/reportes.py`:

```python
with tab_camas:
    st.subheader("🛏️ Camas Bloqueadas")
    st.caption("Camas en CodiCama apuntando a admisiones que ya deberían estar liberadas.")

    st.info(
        "**Dos tipos de bloqueo:**\n\n"
        "🔴 **Bug Sinergia**: admisión CERRADA o ANULADA pero `CodiCama.ConsAdmi` "
        "no se limpió. Requiere intervención de Sinergia.\n\n"
        "🟠 **Proceso incompleto**: `FechEgre` registrada pero nadie ejecutó "
        "'Cerrar Historia'. Cama físicamente vacía. Responsable: personal del servicio actual."
    )

    with st.spinner("Cargando datos de camas..."):
        try:
            df_bug    = get_camas_bug_sinergia(conn)
            df_proc   = get_camas_proceso_incompleto(conn)
            df_serv   = get_camas_resumen_por_servicio(conn)
            camas_ok  = True
        except Exception as e:
            st.error(f"Error: {e}")
            camas_ok = False

    if camas_ok:
        # ── KPIs ─────────────────────────────────────────────────────
        k1, k2, k3 = st.columns(3)
        k1.metric("🔴 Bug Sinergia",          len(df_bug),
                  delta="Requiere parche técnico", delta_color="inverse")
        k2.metric("🟠 Proceso incompleto",     len(df_proc),
                  delta="Personal debe cerrar", delta_color="inverse")
        k3.metric("Total bloqueadas",          len(df_bug) + len(df_proc))

        st.divider()

        # ── Resumen por servicio ──────────────────────────────────────
        st.markdown("#### Bloqueos por servicio")
        if not df_serv.empty:
            import plotly.express as px
            fig_serv = px.bar(
                df_serv.head(15),
                x='CodiServ', y='total_bloqueadas',
                color_discrete_sequence=['#E53935'],
                text='total_bloqueadas',
                labels={'CodiServ': 'Servicio', 'total_bloqueadas': 'Camas bloqueadas'},
                height=320,
            )
            fig_serv.update_layout(xaxis_title='Código servicio', showlegend=False)
            fig_serv.update_traces(textposition='outside')
            st.plotly_chart(fig_serv, use_container_width=True)

        st.divider()

        # ── Tabs internos ─────────────────────────────────────────────
        sub_bug, sub_proc = st.tabs(["🔴 Bug Sinergia", "🟠 Proceso Incompleto"])

        with sub_bug:
            st.markdown(f"**{len(df_bug)} camas** con admisión CERRADA/ANULADA sin liberar")
            if not df_bug.empty:
                st.dataframe(df_bug, use_container_width=True, hide_index=True)
                import io
                buf = io.BytesIO()
                df_bug.to_excel(buf, index=False, engine='openpyxl')
                buf.seek(0)
                st.download_button("⬇️ Exportar Bug Sinergia", data=buf,
                                   file_name="camas_bug_sinergia.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        with sub_proc:
            st.markdown(f"**{len(df_proc)} camas** con egreso registrado pero historia sin cerrar")
            if not df_proc.empty:
                # Semáforo por días desde egreso
                def color_egreso(dias):
                    if dias <= 7:   return "🟡"
                    if dias <= 30:  return "🟠"
                    return "🔴"
                df_proc['alerta'] = df_proc['dias_desde_egreso'].apply(color_egreso)
                st.dataframe(df_proc, use_container_width=True, hide_index=True)
                import io
                buf2 = io.BytesIO()
                df_proc.to_excel(buf2, index=False, engine='openpyxl')
                buf2.seek(0)
                st.download_button("⬇️ Exportar Proceso Incompleto", data=buf2,
                                   file_name="camas_proceso_incompleto.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
```

---

## CAMBIO F — `modules/reportes.py`: Tab "Usuarios SIHOS"

### Queries a agregar en `db/queries.py`:

```python
# ─── USUARIOS SIHOS ───────────────────────────────────────────────────────────

def get_usuarios_resumen(conn) -> pd.DataFrame:
    """Resumen de usuarios con campos clave de gestión."""
    query = """
        SELECT
            u.Login,
            u.Nombre,
            u.CC,
            u.CorrUsua                                          AS email,
            CASE u.Activo WHEN 1 THEN 'Activo' ELSE 'Inactivo' END AS estado,
            CASE u.UsuaAsis WHEN 1 THEN 'Sí' ELSE 'No' END     AS es_asistencial,
            CASE u.PersAtie
                WHEN 1 THEN 'Médico'
                WHEN 2 THEN 'Médico Especialista'
                WHEN 3 THEN 'Enfermera'
                WHEN 4 THEN 'Aux. Enfermería'
                WHEN 5 THEN 'Administrativo'
                ELSE CONCAT('Tipo ', u.PersAtie)
            END AS tipo_personal,
            u.RegiProf                                          AS registro_prof,
            CASE WHEN u.FotoFirm IS NULL OR u.FotoFirm = ''
                 THEN 'No' ELSE 'Sí'
            END                                                 AS tiene_firma,
            g.NombGrup                                          AS grupo_principal,
            g.CodiGrup
        FROM Usuarios u
        LEFT JOIN UsuaGrup ug ON u.Login = ug.Login
        LEFT JOIN GrupUsua g  ON ug.CodiGrup = g.CodiGrup
        ORDER BY u.Activo DESC, u.Nombre
    """
    return pd.read_sql(query, conn)


def get_usuarios_por_grupo(conn) -> pd.DataFrame:
    """Distribución de usuarios por grupo de permisos."""
    query = """
        SELECT
            g.CodiGrup,
            g.NombGrup,
            COUNT(*) AS total_usuarios,
            SUM(CASE WHEN u.Activo = 1 THEN 1 ELSE 0 END) AS activos,
            SUM(CASE WHEN u.Activo != 1 THEN 1 ELSE 0 END) AS inactivos
        FROM UsuaGrup ug
        JOIN GrupUsua g  ON ug.CodiGrup = g.CodiGrup
        JOIN Usuarios u  ON ug.Login = u.Login
        GROUP BY g.CodiGrup, g.NombGrup
        ORDER BY total_usuarios DESC
    """
    return pd.read_sql(query, conn)
```

### Código del tab en `modules/reportes.py`:

```python
with tab_usuarios:
    st.subheader("👥 Usuarios SIHOS")
    st.caption("Gestión de usuarios del sistema — firma digital, grupos de permisos, estado.")

    with st.spinner("Cargando usuarios..."):
        try:
            df_usr  = get_usuarios_resumen(conn)
            df_grp  = get_usuarios_por_grupo(conn)
            usr_ok  = True
        except Exception as e:
            st.error(f"Error: {e}")
            usr_ok = False

    if usr_ok:
        # ── KPIs ─────────────────────────────────────────────────────
        total_usr    = len(df_usr.drop_duplicates('Login'))
        activos      = df_usr.drop_duplicates('Login')['estado'].eq('Activo').sum()
        sin_firma    = df_usr.drop_duplicates('Login')['tiene_firma'].eq('No').sum()
        sin_registro = df_usr.drop_duplicates('Login')['registro_prof'].isna().sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total usuarios",          f"{total_usr:,}")
        k2.metric("Activos",                 f"{activos:,}")
        k3.metric("Sin firma digital",       f"{sin_firma:,}",
                  delta=f"{sin_firma/total_usr*100:.0f}%", delta_color="inverse")
        k4.metric("Sin reg. profesional",    f"{sin_registro:,}",
                  delta=f"{sin_registro/total_usr*100:.0f}%", delta_color="inverse")

        st.divider()

        col_u1, col_u2 = st.columns([2, 1])

        with col_u1:
            st.markdown("#### Top grupos de permisos")
            import plotly.express as px
            fig_grp = px.bar(
                df_grp.head(20),
                x='total_usuarios', y='NombGrup',
                orientation='h',
                color='activos',
                color_continuous_scale='Blues',
                text='total_usuarios',
                labels={'total_usuarios': 'Usuarios', 'NombGrup': ''},
                height=520,
            )
            fig_grp.update_layout(
                yaxis=dict(autorange='reversed'),
                coloraxis_colorbar=dict(title='Activos'),
            )
            fig_grp.update_traces(textposition='outside')
            st.plotly_chart(fig_grp, use_container_width=True)

        with col_u2:
            st.markdown("#### Estado general")
            import plotly.express as px
            est_cnt = df_usr.drop_duplicates('Login')['estado'].value_counts().reset_index()
            est_cnt.columns = ['Estado', 'Cantidad']
            fig_est = px.pie(
                est_cnt, names='Estado', values='Cantidad', hole=0.45,
                color='Estado',
                color_discrete_map={'Activo': '#4CAF50', 'Inactivo': '#9E9E9E'},
            )
            fig_est.update_traces(textinfo='percent+label')
            fig_est.update_layout(showlegend=False, height=250,
                                   margin=dict(t=10,b=10,l=10,r=10))
            st.plotly_chart(fig_est, use_container_width=True)

            st.markdown("#### Firma digital")
            firma_cnt = df_usr.drop_duplicates('Login')['tiene_firma'].value_counts().reset_index()
            firma_cnt.columns = ['Firma', 'Cantidad']
            fig_firma = px.pie(
                firma_cnt, names='Firma', values='Cantidad', hole=0.45,
                color='Firma',
                color_discrete_map={'Sí': '#2196F3', 'No': '#FF5722'},
            )
            fig_firma.update_traces(textinfo='percent+label')
            fig_firma.update_layout(showlegend=False, height=250,
                                     margin=dict(t=10,b=10,l=10,r=10))
            st.plotly_chart(fig_firma, use_container_width=True)

        st.divider()

        # ── Tabla filtrable ───────────────────────────────────────────
        st.markdown("#### Directorio de usuarios")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            estado_f = st.selectbox("Estado", ['Todos', 'Activo', 'Inactivo'],
                                    key="usr_estado")
        with col_f2:
            firma_f = st.selectbox("Firma digital", ['Todos', 'Sí', 'No'],
                                   key="usr_firma")
        with col_f3:
            grupos_disp = ['Todos'] + sorted(df_grp['NombGrup'].dropna().unique().tolist())
            grupo_f = st.selectbox("Grupo", grupos_disp, key="usr_grupo")

        df_filt = df_usr.copy()
        if estado_f != 'Todos':
            df_filt = df_filt[df_filt['estado'] == estado_f]
        if firma_f != 'Todos':
            df_filt = df_filt[df_filt['tiene_firma'] == firma_f]
        if grupo_f != 'Todos':
            df_filt = df_filt[df_filt['grupo_principal'] == grupo_f]

        cols_tabla = ['Login', 'Nombre', 'estado', 'tipo_personal',
                      'grupo_principal', 'tiene_firma', 'registro_prof', 'email']
        st.caption(f"Mostrando {len(df_filt):,} registros")
        st.dataframe(
            df_filt[cols_tabla].rename(columns={
                'Login':          'Login',
                'Nombre':         'Nombre',
                'estado':         'Estado',
                'tipo_personal':  'Tipo',
                'grupo_principal':'Grupo',
                'tiene_firma':    'Firma',
                'registro_prof':  'Reg. Prof.',
                'email':          'Email',
            }),
            use_container_width=True, hide_index=True
        )

        # Descarga
        import io
        buf = io.BytesIO()
        df_filt[cols_tabla].to_excel(buf, index=False, engine='openpyxl')
        buf.seek(0)
        st.download_button(
            "⬇️ Exportar usuarios Excel",
            data=buf,
            file_name="usuarios_sihos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Alertas de seguridad
        st.divider()
        st.markdown("#### ⚠️ Alertas de seguridad")
        grupos_criticos = [1, 11, 199, 194]  # Admin, Admin sistema, Anular Facturas, Abrir-Cerrar
        df_criticos = df_usr[
            df_usr['CodiGrup'].isin(grupos_criticos) & (df_usr['estado'] == 'Activo')
        ][['Login','Nombre','grupo_principal']].drop_duplicates()
        if not df_criticos.empty:
            st.warning(
                f"**{len(df_criticos)} usuarios activos** tienen permisos críticos "
                "(Administrador, Anular Facturas, Abrir-Cerrar Historias):"
            )
            st.dataframe(df_criticos, use_container_width=True, hide_index=True)
```

---

## NOTAS TÉCNICAS GENERALES

1. **Imports necesarios en `db/queries.py`**: todas las funciones nuevas usan `pd.read_sql` — verificar que `import pandas as pd` esté al inicio del archivo.

2. **Imports en `modules/reportes.py`**: agregar al inicio si no están:
```python
import io
import plotly.express as px
import plotly.graph_objects as go
from db.queries import (
    get_admisiones_sin_cerrar_resumen,
    get_admisiones_sin_cerrar_detalle,
    get_camas_bug_sinergia,
    get_camas_proceso_incompleto,
    get_camas_resumen_por_servicio,
    get_usuarios_resumen,
    get_usuarios_por_grupo,
    # ... imports existentes ...
)
```

3. **Fechas `0000-00-00`**: las queries de camas usan `AND a.FechEgre != '0000-00-00'` para evitar falsos positivos con el valor default de MySQL.

4. **Usuarios duplicados**: un usuario puede tener múltiples grupos — `df_usr` tiene una fila por grupo. Usar `.drop_duplicates('Login')` para KPIs de conteo.

5. **Grupos críticos de seguridad** identificados:
   - `CodiGrup=1`: Administrador (2 usuarios activos)
   - `CodiGrup=11`: Administrador del sistema (34 usuarios — revisar)
   - `CodiGrup=194`: Abrir-Cerrar Historias (29 usuarios)
   - `CodiGrup=199`: Anular_Facturas (5 usuarios)

---

## VALIDACIÓN ESPERADA

**Tab Admisiones sin Cerrar**: ~21,554 total, ~605 legítimas, barra más alta en "6. Más de 1 año"

**Tab Camas Bloqueadas**: ~21 Bug Sinergia, ~333 Proceso incompleto, total ~354

**Tab Usuarios SIHOS**: ~2,074 usuarios, 97 grupos, mayoría sin firma digital, alertas de grupos críticos con CodiGrup 1, 11, 194, 199

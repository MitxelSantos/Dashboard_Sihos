# SIHOS Dashboard — Parte 5: Correcciones y Mejoras Visuales

---

## CORRECCIÓN 1 — Bug Pendientes RDA = 0 en pestaña Reportes

**Archivo:** `utils/queries.py`

**Problema:** `created_at BETWEEN fecha_ini AND fecha_fin` interpreta `fecha_fin` como `2026-05-27 00:00:00`, dejando fuera todos los registros del día con hora > 00:00.

**Solución:** reemplazar en `get_rda_summary()` y `get_rda_tabla()` la condición de fecha:

En `get_rda_summary()`, cambiar:
```sql
AND created_at BETWEEN :fecha_inicio AND :fecha_fin
```
Por:
```sql
AND DATE(created_at) BETWEEN :fecha_inicio AND :fecha_fin
```

En `get_rda_tabla()` (el f-string), cambiar:
```sql
AND e.created_at BETWEEN %(fecha_ini)s AND %(fecha_fin)s
```
Por:
```sql
AND DATE(e.created_at) BETWEEN %(fecha_ini)s AND %(fecha_fin)s
```

---

## CORRECCIÓN 2 — Home: admisiones muestran solo 2 de 4 tipos

**Archivo:** `modules/home.py`

**Problema:** la sección "Admisiones de Hoy" solo muestra Urgencias y Hospitalización. Faltan Consulta Externa y PyP.

**Solución:** reemplazar el bloque de métricas de admisiones en `render_inicio()`. Localizar el bloque `col1, col2, col3, col4 = st.columns(4)` bajo `render_section_banner("🏥", "Admisiones de Hoy")` y reemplazarlo con:

```python
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    render_metric_card(
        "📊", "ADMISIONES",
        f"{int(adm.get('Total_Admisiones', 0)):,}",
        COLORS['primary'], COLORS['secondary']
    )
with col2:
    render_metric_card(
        "🚨", "URGENCIAS",
        f"{int(adm.get('Urgencias', 0)):,}",
        COLORS['warning'], COLORS['danger']
    )
with col3:
    render_metric_card(
        "🛏️", "HOSPITALIZACIÓN",
        f"{int(adm.get('Hospitalizacion', 0)):,}",
        COLORS['info'], COLORS['primary']
    )
with col4:
    render_metric_card(
        "👨‍⚕️", "CONSULTA EXTERNA",
        f"{int(adm.get('Consulta_Externa', 0)):,}",
        COLORS['success'], COLORS['secondary']
    )
with col5:
    render_metric_card(
        "💚", "PyP",
        f"{int(adm.get('PyP', 0)):,}",
        COLORS['secondary'], COLORS['success']
    )
```

La query `get_estadisticas_admisiones_hoy()` ya retorna los campos `Consulta_Externa` y `PyP` — no requiere cambio en queries.

---

## CORRECCIÓN 3 — Admisiones: diagnósticos muestran código, no nombre

**Archivos:** `requirements.txt` y `utils/queries.py` y `modules/admisiones.py`

**Problema:** `DiagIngr` es código CIE-10 pero SIHOS no tiene tabla catálogo. Se usará la librería `simple-icd-10-cm` que incluye todo el catálogo CIE-10 en Python.

### Paso 1 — Agregar dependencia en `requirements.txt`:
```
simple-icd-10-cm>=2.0.0
```

### Paso 2 — En `modules/admisiones.py`, agregar al inicio del archivo:
```python
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
```

### Paso 3 — En `modules/admisiones.py`, después de cargar `data['top_diagnosticos']`, agregar:
```python
# Enriquecer códigos con nombres CIE-10
if not data['top_diagnosticos'].empty and _ICD10_DISPONIBLE:
    data['top_diagnosticos']['Codigo'] = (
        data['top_diagnosticos']['Codigo']
        .apply(_nombre_diagnostico)
    )
```

**Nota:** si `simple-icd-10-cm` no está disponible en el entorno, el dashboard sigue funcionando mostrando solo el código — no rompe nada.

---

## CORRECCIÓN 4 — Ocupación: agregar gráfica comparativa camas vs ocupadas

**Archivo:** `modules/ocupacion.py`

**Problema:** la pestaña de ocupación solo muestra porcentaje pero no la comparativa visual de camas totales vs ocupadas por servicio, que es más intuitiva para gestión.

**Solución:** en `render_ocupacion()`, dentro de la distribución "Por Servicio", agregar después del gráfico actual esta gráfica comparativa:

Localizar el bloque `with st.expander("📋 Ver tabla detallada"):` bajo la distribución de ocupación y agregar ANTES del expander:

```python
# Gráfica comparativa Total vs Ocupadas por servicio
if opcion_dist == "Por Servicio" and not datos_dist.empty:
    st.markdown("#### 🛏️ Camas totales vs ocupadas por servicio")
    df_serv_comp = data['por_servicio'].copy()
    df_serv_comp = df_serv_comp[df_serv_comp['Total_Camas'] > 0].sort_values(
        'Ocupadas', ascending=True
    )
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(
        name='Libres',
        y=df_serv_comp['Servicio'],
        x=df_serv_comp['Total_Camas'] - df_serv_comp['Ocupadas'],
        orientation='h',
        marker_color=COLORS['success'],
        opacity=0.7
    ))
    fig_comp.add_trace(go.Bar(
        name='Ocupadas',
        y=df_serv_comp['Servicio'],
        x=df_serv_comp['Ocupadas'],
        orientation='h',
        marker_color=COLORS['danger'],
        text=df_serv_comp['Porcentaje_Ocupacion'].apply(lambda x: f"{x:.0f}%"),
        textposition='inside'
    ))
    fig_comp.update_layout(
        barmode='stack',
        height=max(350, len(df_serv_comp) * 35),
        xaxis_title='Número de camas',
        legend=dict(orientation='h', y=1.05),
        hovermode='y unified'
    )
    st.plotly_chart(fig_comp, use_container_width=True)
```

---

## MEJORA — Profesionales: desglose por módulo clínico

**Archivo:** `utils/queries.py` y `modules/profesionales.py`

**Contexto:** `RipsCons.CodiModu` contiene el módulo clínico (5=Consulta Externa, 6=Urgencias, 8=Hospitalización/UCI, 9=Odontología, 10=Laboratorio, 15=PyP, 27=Cirugía, 28=Procedimientos, 38=Terapias). Esto da mucho más detalle que solo `TipoAten`.

### En `utils/queries.py` — agregar método `get_atenciones_por_modulo()`:

```python
def get_atenciones_por_modulo(self):
    """Distribución de atenciones por módulo clínico (más granular que TipoAten)"""
    return """
    SELECT
        CASE CodiModu
            WHEN 5  THEN 'Consulta Externa'
            WHEN 6  THEN 'Urgencias'
            WHEN 8  THEN 'Hospitalización/UCI'
            WHEN 9  THEN 'Odontología'
            WHEN 10 THEN 'Laboratorio'
            WHEN 15 THEN 'PyP'
            WHEN 27 THEN 'Cirugía'
            WHEN 28 THEN 'Procedimientos'
            WHEN 38 THEN 'Terapias'
            ELSE CONCAT('Módulo ', CodiModu)
        END                         AS Modulo,
        COUNT(*)                    AS Total_Atenciones,
        COUNT(DISTINCT UsuaCons)    AS Profesionales_Activos,
        COUNT(CASE WHEN EstaReal = 1 THEN 1 END) AS Realizadas,
        ROUND(
            COUNT(CASE WHEN EstaReal = 1 THEN 1 END) * 100.0
            / NULLIF(COUNT(*), 0), 1
        )                           AS PctCumplimiento
    FROM RipsCons
    WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
      AND UsuaCons IS NOT NULL
      AND UsuaCons != ''
    GROUP BY CodiModu
    ORDER BY Total_Atenciones DESC
    """
```

### En `utils/queries.py` — agregar método `get_heatmap_hora_profesional()`:

```python
def get_heatmap_hora_profesional(self):
    """Distribución de atenciones por hora del día y día de la semana"""
    return """
    SELECT
        HOUR(HoraCons)      AS Hora,
        DAYOFWEEK(FechCons) AS DiaSemana,
        CASE DAYOFWEEK(FechCons)
            WHEN 1 THEN 'Dom'
            WHEN 2 THEN 'Lun'
            WHEN 3 THEN 'Mar'
            WHEN 4 THEN 'Mié'
            WHEN 5 THEN 'Jue'
            WHEN 6 THEN 'Vie'
            WHEN 7 THEN 'Sáb'
        END                 AS NombreDia,
        COUNT(*)            AS Total
    FROM RipsCons
    WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
      AND HoraCons IS NOT NULL
      AND UsuaCons IS NOT NULL
      AND UsuaCons != ''
    GROUP BY HOUR(HoraCons), DAYOFWEEK(FechCons)
    ORDER BY DiaSemana, Hora
    """
```

### En `modules/profesionales.py` — cargar los nuevos datos:

Dentro de `load_profesionales_data()`, al final del bloque `try`, agregar:

```python
data['por_modulo'] = db.execute_query(
    queries.get_atenciones_por_modulo(), params
)
data['heatmap_hora'] = db.execute_query(
    queries.get_heatmap_hora_profesional(), params
)
```

### En `modules/profesionales.py` — agregar sección "Por Módulo Clínico":

Agregar después de `render_section_divider()` que sigue a las métricas principales, antes de la sección DISTRIBUCIÓN:

```python
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
```

### En `modules/profesionales.py` — agregar Heatmap al final:

Agregar antes de `render_footer()`:

```python
render_section_divider()

# =======================================================================
# SECCIÓN: MAPA DE CALOR — CARGA POR HORA Y DÍA
# =======================================================================
render_section_banner("🌡️", "Mapa de Calor — Carga Horaria", rango_fechas)

if not data['heatmap_hora'].empty:
    import numpy as np

    df_heat = data['heatmap_hora'].copy()

    # Pivotear para heatmap: filas=Hora, columnas=Día
    orden_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    pivot = df_heat.pivot_table(
        index='Hora', columns='NombreDia',
        values='Total', aggfunc='sum', fill_value=0
    )
    # Reordenar días
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
```

---

## NOTAS DE IMPLEMENTACIÓN

1. **`simple-icd-10-cm`**: instalar con `pip install simple-icd-10-cm`. Si el entorno VPS no tiene acceso a internet, la librería puede instalarse desde un wheel descargado previamente. El dashboard funciona sin ella (muestra solo código).

2. **Bug pendientes RDA**: el fix es solo cambiar `created_at BETWEEN` por `DATE(created_at) BETWEEN` en dos queries. Cambio mínimo, alto impacto.

3. **Heatmap**: requiere que `HoraCons` no sea NULL en `RipsCons`. Si el gráfico sale vacío, agregar `AND HoraCons != '00:00:00'` al WHERE de `get_heatmap_hora_profesional()`.

4. **Gráfica comparativa ocupación**: usa `data['por_servicio']` que ya se carga en `load_ocupacion_data()` — no requiere query adicional.

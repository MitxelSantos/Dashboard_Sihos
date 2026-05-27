# SIHOS Dashboard — Parte 2: Nuevas secciones

## SCHEMA DE LAS TABLAS NUEVAS

### EnviRda (36.706 registros)
- PK = `id` (bigint)
- `CodiInst` (varchar)
- `ConsAdmi` (varchar) — número largo de admisión, ej. `202605270608`
- `tipo_rda_id` (bigint): **60** = RDA Paciente/Antecedentes, **61** = RDA Consulta Externa
- `estado_id` (bigint): **56** = Enviado, **57** = Pendiente, **58** = Rechazado
- `json` (longtext) — payload FHIR Bundle enviado al Ministerio
- `usuario` (varchar) — usuario SIHOS que generó el envío
- `created_at`, `updated_at`, `deleted_at` (timestamp) — soft delete, `deleted_at IS NULL` = activo

### AudiRda (historial de respuestas del Ministerio)
- PK = `id` (bigint)
- `EnviRda_id` (bigint) — FK a EnviRda.id
- `json_respuesta` (longtext) — respuesta del Ministerio en JSON
- `usuario_id` (varchar)
- `created_at`, `updated_at`, `deleted_at` (timestamp)

**Estructura de json_respuesta:**
- Exitoso: `{"http_code": 200, "respuesta": {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "DocumentReference", "id": "UUID-VIDA-AQUI"}}]}}`
- Rechazado: `{"http_code": 400, "respuesta": {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "details": {"coding": [{"display": "MENSAJE DE ERROR"}]}}]}}`

---

## NUEVA SECCIÓN 1 — Tarjetas RDA en el dashboard principal

Agregar en el dashboard principal una nueva sección de título **"Interoperabilidad RDA"** con 3 tarjetas métricas y un botón de acceso al detalle.

**Query:**
```python
def get_rda_summary(engine, fecha_ini, fecha_fin):
    query = """
    SELECT
        SUM(CASE WHEN estado_id = 56 THEN 1 ELSE 0 END) AS Enviados,
        SUM(CASE WHEN estado_id = 57 THEN 1 ELSE 0 END) AS Pendientes,
        SUM(CASE WHEN estado_id = 58 THEN 1 ELSE 0 END) AS Rechazados,
        COUNT(*) AS Total
    FROM EnviRda
    WHERE deleted_at IS NULL
      AND created_at BETWEEN %(fecha_ini)s AND %(fecha_fin)s
    """
    return pd.read_sql(query, engine, params={"fecha_ini": fecha_ini, "fecha_fin": fecha_fin})
```

**Visualización — 3 columnas:**
```python
row = get_rda_summary(engine, fecha_ini, fecha_fin).iloc[0]
total = row["Total"] or 1

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="🟢 Enviados",
        value=f"{int(row['Enviados']):,}",
        delta=f"{row['Enviados']/total*100:.1f}%"
    )
with col2:
    st.metric(
        label="🟡 Pendientes",
        value=f"{int(row['Pendientes']):,}",
        delta=f"{row['Pendientes']/total*100:.1f}%"
    )
with col3:
    st.metric(
        label="🔴 Rechazados",
        value=f"{int(row['Rechazados']):,}",
        delta=f"{row['Rechazados']/total*100:.1f}%",
        delta_color="inverse"
    )

st.caption("Ver detalle completo en la pestaña **Reportes → Interoperabilidad RDA**")
```

---

## NUEVA SECCIÓN 2 — Pestaña "Reportes"

Agregar una nueva pestaña llamada **"Reportes"** al sistema de pestañas del dashboard.

Dentro de Reportes, crear dos sub-secciones usando `st.tabs`:
1. **"Interoperabilidad RDA"** — implementada completamente
2. **"Otros reportes"** — solo placeholders

---

### Sub-sección: Interoperabilidad RDA

#### Filtros
```python
col_fecha1, col_fecha2, col_estado, col_busqueda = st.columns(4)

with col_fecha1:
    fecha_ini = st.date_input("Fecha inicio", value=date.today().replace(day=1))
with col_fecha2:
    fecha_fin = st.date_input("Fecha fin", value=date.today())
with col_estado:
    estado_opciones = {
        "Todos": None,
        "🟢 Enviado": 56,
        "🟡 Pendiente": 57,
        "🔴 Rechazado": 58
    }
    estado_sel = st.selectbox("Estado", options=list(estado_opciones.keys()))
    estado_id = estado_opciones[estado_sel]
with col_busqueda:
    busqueda = st.text_input("Buscar por admisión", placeholder="Ej: 202605270608")
```

#### Query principal de la tabla
```python
def get_rda_tabla(engine, fecha_ini, fecha_fin, estado_id=None, busqueda=None):
    filtro_estado = "AND e.estado_id = %(estado_id)s" if estado_id else ""
    filtro_busqueda = "AND e.ConsAdmi LIKE %(busqueda)s" if busqueda else ""

    query = f"""
    SELECT
        e.ConsAdmi                          AS Admision,
        COALESCE(p.NombUsua, 'Sin datos')   AS Paciente,
        DATE(MIN(e.created_at))             AS Reportado,
        MAX(CASE WHEN e.tipo_rda_id = 60
            THEN CASE e.estado_id
                WHEN 56 THEN '🟢 Enviado'
                WHEN 57 THEN '🟡 Pendiente'
                WHEN 58 THEN '🔴 Rechazado'
            END END)                        AS RDA_Paciente,
        MAX(CASE WHEN e.tipo_rda_id = 61
            THEN CASE e.estado_id
                WHEN 56 THEN '🟢 Enviado'
                WHEN 57 THEN '🟡 Pendiente'
                WHEN 58 THEN '🔴 Rechazado'
            END END)                        AS RDA_ConsExterna,
        'No Aplica'                         AS RDA_Urg,
        'No Aplica'                         AS RDA_Hosp,
        MAX(e.updated_at)                   AS UltimaActualizacion
    FROM EnviRda e
    LEFT JOIN Admision a ON a.ConsAdmi = e.ConsAdmi
    LEFT JOIN Paciente p ON p.NumeUsua = a.NumeUsua
    WHERE e.deleted_at IS NULL
      AND e.created_at BETWEEN %(fecha_ini)s AND %(fecha_fin)s
      {filtro_estado}
      {filtro_busqueda}
    GROUP BY e.ConsAdmi, p.NombUsua
    ORDER BY MAX(e.created_at) DESC
    LIMIT 500
    """

    params = {"fecha_ini": str(fecha_ini), "fecha_fin": str(fecha_fin)}
    if estado_id:
        params["estado_id"] = estado_id
    if busqueda:
        params["busqueda"] = f"%{busqueda}%"

    return pd.read_sql(query, engine, params=params)
```

#### Renderizar tabla y panel de detalle
```python
df_rda = get_rda_tabla(engine, fecha_ini, fecha_fin, estado_id, busqueda or None)
st.caption(f"{len(df_rda)} admisiones encontradas (máx. 500)")

# Tabla interactiva
seleccion = st.dataframe(
    df_rda,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row"
)

# Panel de detalle al seleccionar una fila
if seleccion.selection.rows:
    fila = df_rda.iloc[seleccion.selection.rows[0]]
    consadmi_sel = fila["Admision"]

    st.divider()
    st.subheader(f"Detalle — Admisión {consadmi_sel}")
    st.write(f"**Paciente:** {fila['Paciente']}")

    df_detalle = get_rda_detalle(engine, consadmi_sel)

    for _, row in df_detalle.iterrows():
        with st.expander(f"{row['TipoRDA']} — {row['Estado']}", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Usuario SIHOS:** {row['UsuarioSIHOS']}")
                st.write(f"**Fecha envío:** {row['FechaEnvio']}")
                st.write(f"**HTTP:** {row['HttpCode']}")
            with col_b:
                if row["HttpCode"] == "200" and row["NumeroVIDA"]:
                    st.success(f"**Número VIDA:** `{row['NumeroVIDA']}`")
                elif row["HttpCode"] == "400" and row["MensajeError"]:
                    st.error(f"**Error:** {row['MensajeError']}")
                else:
                    st.info("Pendiente de procesamiento")
```

#### Query de detalle por admisión
```python
def get_rda_detalle(engine, consadmi):
    query = """
    SELECT
        e.id                AS EnviRda_id,
        e.ConsAdmi,
        CASE e.tipo_rda_id
            WHEN 60 THEN 'RDA Paciente'
            WHEN 61 THEN 'RDA Consulta Externa'
            ELSE CONCAT('Tipo ', e.tipo_rda_id)
        END                 AS TipoRDA,
        CASE e.estado_id
            WHEN 56 THEN '🟢 Enviado'
            WHEN 57 THEN '🟡 Pendiente'
            WHEN 58 THEN '🔴 Rechazado'
        END                 AS Estado,
        e.usuario           AS UsuarioSIHOS,
        e.created_at        AS FechaEnvio,
        JSON_UNQUOTE(JSON_EXTRACT(
            a.json_respuesta,
            '$.respuesta.entry[0].resource.id'
        ))                  AS NumeroVIDA,
        JSON_UNQUOTE(JSON_EXTRACT(
            a.json_respuesta, '$.http_code'
        ))                  AS HttpCode,
        JSON_UNQUOTE(JSON_EXTRACT(
            a.json_respuesta,
            '$.respuesta.issue[0].details.coding[0].display'
        ))                  AS MensajeError,
        a.created_at        AS FechaRespuesta
    FROM EnviRda e
    LEFT JOIN AudiRda a ON a.EnviRda_id = e.id
    WHERE e.ConsAdmi = %(consadmi)s
      AND e.deleted_at IS NULL
    ORDER BY e.tipo_rda_id, a.created_at DESC
    """
    return pd.read_sql(query, engine, params={"consadmi": consadmi})
```

---

### Sub-sección: Otros reportes (placeholders)

```python
st.divider()
st.subheader("Otros reportes")
st.caption("Las siguientes secciones estarán disponibles en próximas versiones.")

col1, col2, col3 = st.columns(3)
for col, nombre, icono in zip(
    [col1, col2, col3],
    ["RIPS", "Resolución 373", "SISMED"],
    ["📄", "📋", "💊"]
):
    with col:
        st.info(f"{icono} **{nombre}**\n\n_Próximamente disponible_")
```

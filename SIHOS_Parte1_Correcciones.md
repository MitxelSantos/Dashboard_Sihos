# SIHOS Dashboard — Parte 1: Correcciones a secciones existentes

## CONFIGURACIÓN CRÍTICA DE CONEXIÓN
Verificar que el engine de SQLAlchemy tenga esta configuración exacta, sin esto los campos con fecha cero lanzan error:
```python
engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}/sihos",
    connect_args={"init_command": "SET SESSION sql_mode=''"}
)
```

---

## CORRECCIÓN 1 — FACTURACIÓN

**Problema:** la query actual usa `EncaFact.ValoTota` como fuente de facturación total, lo que subestima el valor real.

**Solución:** cambiar la fuente a `DetaFact`. El JOIN correcto entre ambas tablas es por `(CodiInst, CodiAno, CodiDocu, NumeFact)` — **sin CodiDocu en el JOIN con FactElec**.

**Query correcta:**
```sql
SELECT
    COALESCE(SUM(df.ValoTota), 0) AS TotalFacturado,
    COUNT(DISTINCT df.ConsAdmi)   AS TotalAdmisiones,
    COUNT(DISTINCT CONCAT(ef.CodiInst, ef.CodiAno, ef.CodiDocu, ef.NumeFact)) AS TotalFacturas
FROM DetaFact df
JOIN EncaFact ef
    ON  ef.CodiInst = df.CodiInst
    AND ef.CodiAno  = df.CodiAno
    AND ef.CodiDocu = df.CodiDocu
    AND ef.NumeFact = df.NumeFact
WHERE ef.Anulado = 0
  AND ef.FechFact BETWEEN %(fecha_ini)s AND %(fecha_fin)s;
```

**Agregar tooltip o nota debajo del KPI:**
> *"Fuente: DetaFact. Puede diferir del reporte nativo SIHOS (~$800M de brecha conocida en mayo 2026)."*

---

## CORRECCIÓN 2 — ESTADO DE CITAS

**Problema:** el filtro de estado puede estar incluyendo códigos internos del sistema (8–95) que inflan los conteos.

**Solución:** agregar `AND EstaCita BETWEEN 1 AND 7` en todas las queries de citas.

**Valores válidos de EstaCita:**
- 1 = Disponible
- 2 = Ocupada
- 3 = Cumplida
- 4 = Incumplida-Paciente
- 5 = Incumplida-Médico
- 6 = Cancelado
- 7 = Incumplida-Sistema

**Query correcta:**
```sql
SELECT
    ec.NombEsta,
    COUNT(*) AS TotalCitas,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS Porcentaje
FROM DetaCita dc
JOIN EstaCita ec ON ec.CodiEsta = dc.EstaCita
WHERE dc.FechCita BETWEEN %(fecha_ini)s AND %(fecha_fin)s
  AND dc.EstaCita BETWEEN 1 AND 7
GROUP BY ec.NombEsta
ORDER BY TotalCitas DESC;
```

**Distribución esperada mayo 2026:** Cumplida ≈ 57.7%, Ocupada ≈ 24.1%, Disponible ≈ 13.4%

---

## CORRECCIÓN 3 — INDICADOR DE OPORTUNIDAD

**Problema:** el dashboard probablemente muestra una sola métrica de oportunidad. Deben ser dos métricas distintas con lógicas diferentes.

**Solución:** mostrar dos KPIs separados:

**KPI 1 — "Espera desde solicitud"** (filtro por FechSoli en el mes):
```sql
SELECT
    ROUND(AVG(DATEDIFF(FechCita, FechSoli)), 2) AS PromEsperaSolicitud,
    COUNT(*) AS TotalCitas
FROM DetaCita
WHERE FechSoli BETWEEN %(fecha_ini)s AND %(fecha_fin)s
  AND EstaCita BETWEEN 1 AND 7
  AND DATEDIFF(FechCita, FechSoli) >= 0;
```
> Agregar tooltip: *"Este valor (~2.5 días) difiere del reporte SIHOS nativo (29.66 días). Pendiente validación con proveedor Sinergia."*

**KPI 2 — "Espera desde asignación"** ✅ validado contra SIHOS (filtro por FechCita en el mes):
```sql
SELECT
    ROUND(AVG(DATEDIFF(FechCita, FechAsig)), 2) AS PromEsperaAsignacion,
    COUNT(*) AS TotalCitas
FROM DetaCita
WHERE FechCita BETWEEN %(fecha_ini)s AND %(fecha_fin)s
  AND EstaCita BETWEEN 1 AND 7
  AND DATEDIFF(FechCita, FechAsig) >= 0;
```
> Valor esperado: ~8.7 días (SIHOS nativo: 7.92 días ✅)

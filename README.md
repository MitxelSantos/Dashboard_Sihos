# Dashboard SIHOS

## Hospital Regional Alfonso Jaramillo Salazar
**Sistema de Información Hospitalaria — Líbano, Tolima**

---

## Descripción

Dashboard centralizado en tiempo real para visualización de indicadores hospitalarios. Construido con Streamlit sobre la base de datos MySQL de SIHOS (sistema de historia clínica del hospital, +1.272 tablas).

---

## Características

- **Login con roles** — admin, gerencia, calidad. Cada rol ve solo las pestañas autorizadas.
- **Credenciales seguras** — ninguna contraseña en el código fuente; todo en `.streamlit/secrets.toml` (excluido de git).
- **Auto-refresh** — actualización automática cada 5 minutos.
- **Módulos independientes** — cada pestaña es un módulo separado en `modules/`.
- **Conexión read-only** a MySQL SIHOS.
- **KPIs con tooltip, no con texto suelto** — cada tarjeta de métrica (`render_metric_card(..., help_text=...)` o `st.metric(..., help=...)`) trae su propia explicación en un ícono ⓘ al pasar el mouse, en vez de `st.caption`/`st.info` fijos ocupando espacio. Ver [Convenciones de código](#convenciones-de-código).
- **Producción individual por profesional** (dentro de Actividad Clínica) — selector de profesional con sus citas, KPIs de cumplimiento, tendencia diaria y distribución por finalidad.

---

## Módulos disponibles

| Pestaña | Tab key | Roles con acceso (según `secrets.toml` actual) |
|---|---|---|
| Home | `home` | Todos |
| Admisiones | `admisiones` | admin, gerencia |
| Facturación | `facturacion` | admin, gerencia |
| Procedimientos | `procedimientos` | admin, calidad |
| Laboratorio | `laboratorio` | *(no configurado — solo admin ve por bypass)* |
| Cirugías | `cirugias` | admin, calidad |
| Ocupación | `ocupacion` | Todos |
| Actividad Clínica (Profesionales + Citas) | `actividad` | *(no configurado — solo admin ve por bypass)* |
| Profesionales *(comparar)* ⚠️ temporal | `profesionales` | admin, gerencia |
| Citas *(comparar)* ⚠️ temporal | `citas` | *(no configurado — solo admin ve por bypass)* |
| Reportes | `reportes` | *(no configurado — solo admin ve por bypass)* |
| Inventario TI | `inventario_ti` | *(no configurado — solo admin ve por bypass)* |
| Consultas SQL | `consultas_sql` | admin |

> `admin` siempre ve **todo** `TAB_ORDER` sin importar lo que diga `secrets.toml` (bypass explícito en `app.py::_tabs_permitidas`). Los demás roles solo ven las claves listadas en `[roles]` de `secrets.toml`. Ahora mismo ese archivo está desactualizado: sigue listando `profesionales` en vez de `actividad`, y no tiene entradas para `laboratorio`, `actividad`, `reportes` ni `inventario_ti` — ver [Pendientes / Deuda técnica](#pendientes--deuda-técnica).

---

## Estructura del proyecto

```
Dashboard_SIHOS/
├── app.py                        # Entrada principal, login, routing por tabs
├── config/
│   └── settings.py               # PAGE_TITLE, TABS_CONFIG, TAB_ORDER, COLORS
├── modules/                      # Un archivo por pestaña
│   ├── home.py                   # Resumen ejecutivo (datos de HOY)
│   ├── admisiones.py
│   ├── facturacion.py
│   ├── procedimientos.py
│   ├── laboratorio.py
│   ├── cirugias.py
│   ├── ocupacion.py
│   ├── actividad.py              # Unifica Profesionales + Citas + Producción individual
│   ├── profesionales.py          # ⚠️ standalone, reconectado temporalmente para comparar
│   ├── citas.py                  # ⚠️ standalone, reconectado temporalmente para comparar
│   ├── reportes.py               # RDA, Res. 373, Admisiones sin Cerrar, Camas Bloqueadas, Usuarios SIHOS, SISMED
│   ├── inventario.py             # Lee inventario_hospital_v1.xlsx (no usa MySQL)
│   └── consultas_sql.py          # Consola SQL ad-hoc (solo SELECT)
├── components/
│   ├── layout.py                 # Header, Sidebar, Footer
│   └── widgets.py                # render_metric_card, tooltips, banners, etc.
├── utils/
│   ├── db_connector.py           # Conexión MySQL (lee de secrets.toml)
│   └── queries.py                # Todas las queries SQL, clase SIHOSQueries
├── assets/
│   ├── logo.png
│   ├── base.css                  # Variables de tema (claro/oscuro)
│   ├── layout.css
│   └── components.css            # ⚠️ código muerto — no se carga en ningún lado, ver Pendientes
├── inventario_hospital_v1.xlsx   # Fuente de datos del módulo Inventario TI
└── .streamlit/
    ├── config.toml               # Tema Streamlit (en git)
    └── secrets.toml              # Credenciales y roles (NO en git)
```

---

## Instalación local

### Prerrequisitos
- Python 3.11+
- Acceso a MySQL SIHOS (red local o IP pública)

### Pasos

```bash
# 1. Clonar
git clone https://github.com/MitxelSantos/Dashboard_Sihos.git
cd Dashboard_Sihos

# 2. Entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Dependencias
pip install -r requirements.txt

# 4. Crear secrets.toml (ver sección siguiente)

# 5. Ejecutar
streamlit run app.py
```

---

## Configuración de credenciales

Crea el archivo `.streamlit/secrets.toml` (nunca se sube a git):

```toml
[database]
host     = "172.16.2.5"       # IP local  |  IP pública en VPS
port     = 3306
database = "sihos"
user     = "usuario_readonly"
password = "contraseña"
charset  = "utf8mb4"

[usuarios.admin]
password = "tu_clave"
rol = "admin"

[usuarios.gerencia]
password = "tu_clave"
rol = "gerencia"

[usuarios.calidad]
password = "tu_clave"
rol = "calidad"

[roles]
admin    = ["home", "admisiones", "facturacion", "procedimientos", "laboratorio", "cirugias", "ocupacion", "actividad", "reportes", "inventario_ti", "consultas_sql"]
gerencia = ["home", "admisiones", "facturacion", "ocupacion", "actividad"]
calidad  = ["home", "procedimientos", "cirugias", "ocupacion"]
```

> Para agregar usuarios o cambiar permisos: edita solo `secrets.toml`, sin tocar código.
> ⚠️ Esta plantilla ya usa `actividad` (la pestaña vigente). El `secrets.toml` real en producción todavía dice `profesionales` — pendiente de actualizar, ver abajo.

---

## Despliegue en VPS (AlmaLinux 8 / WHM)

**Ruta real en producción:** `/home/dashboard_sihos` (verificada en vivo — no es `/home/hospital/dashboard_sihos` como sugería una versión anterior de este README).

### 1. Verificar conectividad MySQL desde el VPS
```bash
mysql -u rvargasri -p -h 190.65.221.22 -P 3306 sihos
```

### 2. Instalar dependencias en el VPS
```bash
dnf install python3.11 python3.11-pip git -y
```

### 3. Clonar y configurar
```bash
git clone https://github.com/MitxelSantos/Dashboard_Sihos.git /home/dashboard_sihos
cd /home/dashboard_sihos
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Crear secrets.toml en el VPS
```bash
mkdir -p .streamlit
nano .streamlit/secrets.toml
# Igual que el local pero con host = "190.65.221.22"
```

### 5. Servicio systemd
El servicio ya existe y corre activo en producción: `dashboard-sihos.service` (puerto 8501, `127.0.0.1` únicamente — expuesto al exterior vía el proxy Apache). Confirmado con `systemctl list-units --type=service` → `dashboard-sihos.service   loaded   active   running`.

```bash
systemctl enable dashboard-sihos
systemctl start dashboard-sihos
```

### 6. Virtual host Apache (WHM)
Proxy desde el subdominio hacia `127.0.0.1:8501` con soporte WebSocket.

### 7. Actualizar el VPS después de un cambio (flujo verificado)

Desde tu máquina local, sube el cambio a GitHub:
```bash
git add -A
git commit -m "mensaje descriptivo"
git push origin main
```

Luego, por SSH en el VPS:
```bash
cd /home/dashboard_sihos
git pull origin main
source venv/bin/activate
pip install -r requirements.txt      # solo si cambiaron dependencias
sudo systemctl restart dashboard-sihos
systemctl status dashboard-sihos --no-pager     # confirmar "active (running)"
```

Si algo falla tras el restart, revisa el log en vivo:
```bash
journalctl -u dashboard-sihos -n 50 --no-pager
```

---

## Convenciones de código

### KPIs, gráficas y tooltips
No uses `st.caption` / `st.info` / `st.warning` sueltos solo para explicar qué significa un número o una gráfica. En su lugar, usa el ícono ⓘ (definido en el `<style>` embebido de `components/layout.py::render_header()` — **no** en `assets/*.css`, que es código muerto, ver Pendientes):
- `render_metric_card(emoji, title, value, color_start, color_end, help_text="...")` — tarjetas de KPI.
- `st.metric(label, value, help="...")` — tooltip nativo de Streamlit, mismo criterio.
- `render_section_banner(icon, title, fecha_rango=None, help_text="...")` — banner de sección con gradiente; usa automáticamente la insignia clara (`.metric-help-inverse`) para verse bien sobre el fondo de color.
- `render_heading_help(text, help_text, tag="h4")` — para encabezados sueltos (`st.markdown("#### ...")`, `st.subheader(...)`) que preceden una gráfica o tabla.

Nota: `st.plotly_chart()` (Streamlit 1.57) **no** tiene parámetro `help=` nativo — por eso `render_heading_help`/`render_section_banner` existen: se pone el ícono en el encabezado justo antes del `st.plotly_chart(...)`, quitando el `title=` de Plotly si hace falta espacio.

Deja texto visible (captions/warnings) solo para alertas operativas **activas** que no son la definición de un KPI/gráfica — datos que cambian y ameritan visibilidad permanente (ej. "este valor difiere del reporte nativo SIHOS, pendiente de validar con el proveedor", "X camas bloqueadas, revisar"). Las explicaciones de metodología fijas (qué excluye un promedio, qué códigos cubre un filtro, de qué tabla sale un dato) van en el tooltip.

### Agregar un nuevo módulo
1. Crear `modules/nuevo_modulo.py` con función `render_nuevo_modulo()`
2. Añadir entrada en `TABS_CONFIG` y `TAB_ORDER` en `config/settings.py`
3. Importar y registrar en `tab_functions` en `app.py`
4. Añadir el key en los roles que deben verlo en `secrets.toml`

---

## Notas de Schema SIHOS

La base de datos SIHOS tiene campos cuyo nombre no refleja su semántica real, y varios usan convenciones **distintas entre tablas**. Verificado en vivo contra la base de producción — no asumir, confirmar antes de escribir una query nueva sobre estos campos:

| Tabla.Campo | Significado real | Cómo se verificó |
|---|---|---|
| `Admision.TipoAten` | 1=Consulta Externa, 2=Hospitalización, 3=Urgencias, 4=PyP | Corregido en mayo 2026 (estaba invertido 1↔3) |
| `Admision.Cerrado` | 1=Cerrada, 2=**Activa** (contraintuitivo). **`Cerrado=2` por sí solo YA significa "sin cerrar"** — no asumir que también hay que exigir `FechEgre IS NULL`: una historia puede tener `FechEgre` con valor y seguir en `Cerrado=2` (le falta el clic de "Cerrar Historia"), y SIHOS la sigue mostrando como abierta | `information_schema.COLUMNS` + distribución de datos; confirmado sep-2026 con 2 casos reales de Gineco-Obstetricia que el dashboard omitía por exigir de más `FechEgre IS NULL` |
| `Admision.Anulado` | 1=Anulada, 2=**Válida/no anulada** (mayoría de los registros) | Confirmado sep-2026: comentario de columna + 812,132 de 820,009 registros = 2 |
| `DetaCita.EstaCita` | 1=Disponible, 2=Ocupada, 3=**Cumplida**, 4=Incumplida-Paciente, 5=Incumplida-Médico, 6=Cancelado, 7=Incumplida-Sistema. Códigos ≥8 son **tipos de slot internos de agenda** (no resultados de cita) | Confirmado sep-2026 contra la tabla de referencia `EstaCita` (columna `NombEsta`) |
| `CodiCama.ConsAdmi` | Nunca se limpia al dar de alta al paciente — **no sirve solo** para medir ocupación | Hay que cruzar siempre con `Admision` (`Cerrado=2 AND Anulado=2 AND FechEgre IS NULL`) |
| `Admision.CodiServ` vs `Admision.ServEgre` | `CodiServ` = "Servicio de **Ingreso**" (fijo, no se actualiza con traslados). `ServEgre` = "Servicio **Actual** y/o de Egreso" — el que hay que usar para "¿dónde está el paciente ahora?" | Confirmado sep-2026: `information_schema.COLUMNS` + comparación en vivo — agrupar "admisiones sin cerrar por área" por `CodiServ` subestimaba Urgencias-Observación (1 vs 43 reales con `ServEgre`) |
| `EncaFact.CodiDocu` | Siempre `'LIQ'` (liquidación interna). Las facturas electrónicas están en `FactElec` (`CodiDocu='FE'`) | — |
| `ActoQuir` | El cirujano es `UsuaDigi`, **no** `MediCiru` (ese campo no existe) | — |
| Campos "usuario" (`UsuaDigi`, `UsuaModi`, `UsuaCons`, `EnviRda.usuario`, etc.) | Guardan el **login** de SIHOS, no el nombre de la persona. Para mostrar el nombre: `LEFT JOIN Usuarios u ON u.Login = <campo>` + `COALESCE(u.Nombre, <campo>)` (fallback al login si no hay match) | Confirmado sep-2026: 501/501 logins de `Admision` y 311/311 de `EnviRda` cruzan con `Usuarios.Login`; `Usuarios.Nombre` nunca vacío en los 2,147 usuarios |
| Fechas `'0000-00-00'` | Frecuentes en columnas DATE (`FechEgre`, `FechModi`, etc.). Requieren `NULLIF(campo, '0000-00-00')` o la conexión truena con "Zero date value prohibited" | La conexión ya usa `init_command="SET SESSION sql_mode=''"` en `db_connector.py` |
| `EncaFact.Causado` | 0=**Preliminar** (liquidación creada, ítems ya en `DetaFact`, pero **todo el encabezado en $0**: `ValoTota`, `SubTota`, `ValoIVA`, `ValoCopa`, `ValoEAPB`, `ValoUsua`), 1=**Causada** (encabezado ya calculado y confiable). **Nunca sumar `EncaFact.ValoTota` sin filtrar por `Causado`** — para el valor real usar siempre `DetaFact.ValoTota` (agregado por factura), que está poblado sin importar el estado de causación | Confirmado sep-2026: 2,980 de 56,346 liquidaciones/mes con `Causado=0`, TODAS con encabezado en $0 pero con detalle real; 7,269 liquidaciones históricas así ($4,845M ocultos); diferencia agregada de ~$2,300M/mes entre sumar `EncaFact.ValoTota` vs `DetaFact.ValoTota` |
| `EncaFact.ValoCopa` / `ValoEAPB` / `ValoUsua` | Copago del usuario / valor cobrado a la EPS-EAPB / total a cargo del usuario. Solo existen en `EncaFact` (no hay ese desglose en `DetaFact`), así que solo son confiables con `Causado=1` (ver fila de arriba) | Confirmado sep-2026 vía `information_schema.COLUMNS` (`COLUMN_COMMENT`) |
| `EncaFact.TipoAfil` | Código de 1 letra (A/B/C/D/E/P) — **existe tabla catálogo** `TipoAfil` (`CodiTipo`→`NombTipo`) con los nombres reales: A=Adicional, B=Beneficiario, C=Cotizante, D=No Aplica, E=Subsidiado, P=Particular. No hardcodear un `CASE` — usar `LEFT JOIN TipoAfil` | Confirmado sep-2026: el `CASE` que traía el dashboard ni siquiera contemplaba E/P (cortesía de haber sido escrito a mano sin consultar el catálogo) |
| `EncaFact.UsuaDigi` / `UsuaAnul` | `UsuaDigi` = quién **digitó/creó** la liquidación ("facturador"). `UsuaAnul` = quién **ejecutó la anulación** — puede ser una persona distinta al facturador original. `CausAnul` (int) referencia la tabla catálogo `CausAnul` (`CodiCaus`→`NombCaus`) con el motivo real de la anulación | Confirmado sep-2026 vía `information_schema.COLUMNS` + catálogo `CausAnul` |
| `EncaFact.NotaAnul` | Texto libre que escribe el facturador al anular (varchar 255, suele traer `\n` final). Es distinto de `CausAnul` (código del catálogo `CausAnul`): ambos coexisten — de 433 anuladas desde ago-2026, 313 traen nota y causa, 120 ninguna. `FechAnul`/`UsuaAnul` completan el registro de la anulación | Confirmado sep-2026 en vivo |
| `DetaFact.FechDigi` vs `EncaFact.FechFact` | `FechFact` = fecha de la liquidación; `DetaFact.FechDigi` = fecha en que se digitó cada línea. Para un mismo mes dan totales distintos (agosto 2026: $9,876M por FechFact vs $12,294M por FechDigi, no anuladas) porque las líneas de una liquidación pueden digitarse después. `DetaFact.FechServ` viene vacío | Confirmado sep-2026; criterio del reporte nativo SIHOS por confirmar |
| `Cartera` | Tabla existe (columnas `ValoTota`/`Recaudo`/`Saldo`) pero está **vacía** en producción — no usarla como fuente de estado de cartera/recaudo | Confirmado sep-2026: `SELECT COUNT(*)` = 0 |

**Cómo verificar un campo dudoso en vivo (sin tocar datos):**
```sql
-- 1. Ver qué dice el propio schema
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '<tabla>' AND COLUMN_NAME = '<campo>';

-- 2. Ver la distribución real de valores (el valor mayoritario casi siempre es el "caso normal")
SELECT <campo>, COUNT(*) AS total FROM <tabla> GROUP BY <campo> ORDER BY <campo>;

-- 3. Si existe una tabla de referencia/catálogo (ej. EstaCita, CodiServ), cruzarla directamente
SELECT CodiEsta, NombEsta FROM EstaCita ORDER BY CodiEsta;
```

---

## Pendientes / Deuda técnica

- **`modules/profesionales.py` y `modules/citas.py` reconectados temporalmente** (tabs "Profesionales (comparar)" y "Citas (comparar)", sep-2026) solo para comparar contra `modules/actividad.py`, que las reemplazó pero salió más reducido: le faltan el selector de tipo de gráfica en Distribución (Pie/Bar Horizontal/Bar Agrupadas/Sunburst/Treemap/Funnel) y toda la sección de Tendencias (6-7 métricas) que sí tienen los módulos standalone. **Decisión pendiente:** o se le devuelve esa funcionalidad a `actividad.py` y se borran `profesionales.py`/`citas.py`, o se documenta por qué se simplificó a propósito. Mientras tanto no dejar ambas versiones activas en producción — es código residual.
- **`secrets.toml` desincronizado con `TAB_ORDER`**: `[roles]` todavía usa la clave `profesionales` (no `actividad`) y no tiene entradas para `laboratorio`, `actividad`, `reportes` ni `inventario_ti` — esos roles (gerencia, calidad) solo ven esas pestañas si son `admin`. Actualizar `secrets.toml` (no se versiona en git, hay que hacerlo a mano en cada entorno) cuando se resuelva el punto anterior.
- **Queries en `utils/queries.py` sin ningún módulo que las llame** (candidatas a limpiar o a functionality pendiente de conectar): `get_admisiones_abiertas`, `get_cierres_tardios`, `get_ocupacion_general`, `get_rotacion_camas`, `get_distribucion_tipo_cama`, `get_ocupacion_por_uci`, `get_historico_ocupacion`, `get_tendencia_semanal_procedimientos`.
- **`assets/base.css`, `assets/layout.css` y `assets/components.css` son código muerto**: ningún archivo del proyecto los lee ni los inyecta (confirmado con `grep -r "\.css"` sobre todo el repo). Todo el CSS que realmente se aplica está embebido en un bloque `<style>` dentro de `components/layout.py::render_header()`, que además define su propia copia de `.metric-card`/`.metric-label` distinta a la de `assets/components.css`. Esto causó un bug real (sep-2026): el tooltip `.metric-help` de los KPIs se agregó primero solo en `assets/components.css` y no tuvo ningún efecto visual — el `?` salía como texto plano pegado al título. Decidir: o se conecta `assets/*.css` de verdad (cargarlo con `st.markdown(f"&lt;style&gt;{open('assets/x.css').read()}&lt;/style&gt;", unsafe_allow_html=True)`) y se borra el CSS duplicado de `layout.py`, o se borran los archivos `assets/*.css` para no confundir a futuro. Mientras tanto, **cualquier cambio de estilo visual hay que hacerlo en `components/layout.py`**, no en `assets/`.

---

## Troubleshooting

**Error de conexión BD**
- Verificar que el puerto 3306 esté abierto: `Test-NetConnection -ComputerName <IP> -Port 3306`
- Verificar permisos del usuario MySQL desde la IP del VPS

**secrets.toml no encontrado**
- Verificar que existe en `.streamlit/secrets.toml` relativo al directorio de ejecución

**WebSocket desconectado en proxy**
- Asegurarse de que el virtual host tenga configurado el upgrade de WebSocket

---

## Seguridad

- Conexión MySQL con usuario de **solo lectura**
- Credenciales en `secrets.toml`, excluido de git en `.gitignore`
- Login con roles antes de cualquier carga de datos
- HTTPS recomendado en producción (AutoSSL en cPanel)

---

## Changelog

### v2.6 (2026-09-21)
- **Corregido cuelgue de Facturación ("Running load_facturacion_detalle...")**: causa raíz encontrada en el conector — `DatabaseConnector` nunca cerraba sus conexiones (`get_db_connector()` crea una instancia nueva por llamada) ni tenía timeout. El servidor MySQL mostró `Max_used_connections=501` sobre `max_connections=500` (compartido con el SIHOS de producción) y `wait_timeout=21000s` (≈5.8 h por conexión huérfana). Ahora `execute_query` cierra la conexión en `finally` y `connect()` usa `connection_timeout=15`. Además la query maestra de Facturación acota la agregación de `DetaFact` (3.4M filas) al rango de fechas (2.9 s → 0.9 s por mes; 6.7 s para todo el año) y `Rango` se calcula vectorizado con `pd.cut`.
- **Por Facturador**: el slider ya no se limita a 30 — su máximo es el total de facturadores del período (había ~43-57). En la vista Anulaciones ahora se muestran también `Facturador`, `FechaAnulacion`, `CausaAnulacion` (catálogo) y **`MotivoAnulacion`** = `EncaFact.NotaAnul`, el texto libre que escribe el facturador al anular (varchar 255, con saltos de línea que se limpian). Ver Notas de Schema.
- **Multiselección en las gráficas de barras interactivas** (Distribución y Por Facturador): Shift+clic sobre varias barras, o arrastrar un recuadro (`selection_mode=("points","box")`); la tabla única filtra con todas las seleccionadas. Verificado en vivo (URGENCIAS + CIRUGIA). Nota: cada interacción re-ejecuta el script completo (todas las pestañas), así que la tabla tarda unos segundos en actualizarse.
- **Timeout de sesión**: de 2 h fijas a 12 h por defecto, configurable en `.streamlit/secrets.toml` (`[sesion]` → `timeout_horas = 12`). Aclaración: si Streamlit pierde la conexión WebSocket (laptop suspendido, pestaña dormida), el estado de sesión se pierde igual y pide login de nuevo — eso no lo controla este timeout.
- **Admisiones → nueva sección "Listado de Admisiones — Servicio de Egreso"** (`get_admisiones_listado_egreso`): admisiones válidas con ingreso en el rango, con servicio de ingreso (`CodiServ`), servicio de egreso/actual (`ServEgre`), estado (sin cerrar/cerrada), usuario que abrió (nombre), filtros por tipo/servicio/estado y descarga CSV/Excel.
- **Pendiente de decisión (dinero facturado de agosto)**: por `EncaFact.FechFact` agosto suma $9,876M (liquidaciones no anuladas); sumando las líneas `DetaFact` por su fecha de digitación (`DetaFact.FechDigi`) suma $12,294M ($12,472M incluyendo anuladas) — más cercano a los ~13 mil millones que reporta Facturación. Hay que confirmar con qué fecha/criterio calcula el reporte nativo de SIHOS antes de cambiar el dashboard.

### v2.5 (2026-09-18) — Ajustes tras retro de la v2.4 de Facturación
- **Quitada la tarjeta "TOTAL A CARGO USUARIO"** por redundante: verificado en vivo que `EncaFact.ValoUsua` es idéntico a `ValoCopa` en el 99.986% de las liquidaciones causadas históricas (789,982 de 790,091) — no aportaba información nueva frente a "COPAGO (USUARIO)".
- **Corregido solapamiento visual de las tarjetas KPI**: con valores grandes (ej. `$7,340,542,955`) el texto partía a 2 líneas y se salía por fuera de `.metric-card` (que no tiene alto fijo, no crecía en sync). `render_metric_card()` ahora usa un tamaño de fuente dinámico según la longitud del valor (2.5rem / 1.9rem / 1.5rem) + `white-space: nowrap`. Aplica a **todo el dashboard**, no solo Facturación.
- **Una sola tabla interactiva en vez de dos** (Distribución y Por Facturador): antes había una tabla agregada fija (en expander) + una tabla de detalle que aparecía aparte al hacer clic — ahora es **una única tabla** que muestra el agregado por defecto y cambia a mostrar el detalle de la categoría/facturador clicado, con un botón **"🔄 Ver todo"** que remonta la gráfica (nueva `key`) y la tabla de vuelta a la vista general — clic y botón siempre sincronizados.
- **Eliminada la sección "Top Facturas Más Altas"** (redundante con el resto del tab, a pedido del usuario).
- **Actualizadas las tarjetas de Facturación en Home** (`modules/home.py`): quitada la nota desactualizada "~$800M de brecha conocida" (ya no aplica, esa brecha ERA el bug de `Causado` que se corrigió en v2.4); agregada una 4ª tarjeta **"PENDIENTES DE CAUSAR"** (liquidaciones de hoy con `Causado=0`), para que Home hable el mismo idioma que el tab Facturación. `get_facturacion_hoy()` ahora también devuelve `Valor_Pendiente`/`Facturas_Pendientes`.

### v2.4 (2026-09-18) — Rediseño completo de Facturación
Retroalimentación del área de Facturación sobre 9 puntos; los 5 primeros eran un mismo
bug de fondo, los otros 4 funcionalidad nueva. Rediseño arquitectónico: **una sola query**
(`get_facturacion_detalle_periodo()`, a nivel de factura individual) alimenta ahora TODO
el tab — KPIs, distribución, top facturas, por facturador — todo calculado con pandas
sobre ese mismo DataFrame, reemplazando las 8 queries independientes que tenía antes
(`get_estadisticas_facturacion`, `get_facturacion_por_rango/_tipo_afiliacion/_servicio/
_tipo_documento/_estado/_mes`, `get_top_facturas_altas`, `get_analisis_cartera`,
`get_indicadores_recaudo` — todas eliminadas, ninguna se usaba fuera de este módulo).
- **Corregido bug real** (causa de los puntos 1 y 3 reportados): las tarjetas KPI sumaban `DetaFact.ValoTota` (detalle, siempre real) mientras las gráficas de distribución sumaban `EncaFact.ValoTota` (encabezado) — y el encabezado queda en **$0** mientras la liquidación no ha sido "causada" (`Causado=0`), aunque el detalle ya tenga los valores reales. Impacto medido: ~$2,300M/mes invisibles en las gráficas de distribución, top facturas e indicadores de recaudo. Ver Notas de Schema SIHOS (`EncaFact.Causado`). Todo el dashboard ahora suma siempre desde `DetaFact`.
- **KPIs separados en dos secciones** (punto 1, decisión del usuario): "💰 Facturado (causado)" (facturas, valor, promedio, máxima — solo `Causado=1`) y "🕐 Pendiente de Causar" (conteo y valor de liquidaciones con `Causado=0`), en vez de un solo bloque mezclando ambos estados.
- **Agregado desglose Copago / EPS-EAPB / Usuario** (punto 2): 3 tarjetas nuevas desde `EncaFact.ValoCopa`/`ValoEAPB`/`ValoUsua`, con nota de que solo aplican a facturas causadas.
- **Corregido catálogo de Tipo de Afiliación** (punto 5): existía una tabla `TipoAfil` real con los nombres (Adicional/Beneficiario/Cotizante/No Aplica/Subsidiado/Particular) que el dashboard ignoraba — tenía un `CASE` hardcodeado que ni siquiera cubría todos los códigos (E/P caían en "No Especificado"). Ahora hace `LEFT JOIN TipoAfil`.
- **Eliminadas** "Distribución por Tipo de Documento" y "Distribución por Mes" (puntos 6 y 7 — el usuario las consideró prescindibles).
- **Rediseñado "Estado"** (punto 8): de Activa/Anulada a **Preliminar / Causada / Anulada** (usa `Causado`+`Anulado`), la única granularidad real que existe en el esquema.
- **Gráficas interactivas con drill-down** (punto 4): las 4 opciones de Distribución (Servicio, Rangos, Tipo de Afiliación, Estado) usan `st.plotly_chart(..., on_select="rerun")` — clic en una porción/barra muestra debajo la tabla de facturas de esa categoría, descargable en CSV/Excel. **Importante — limitación real de Plotly.js confirmada instrumentando los eventos JS en vivo**: solo las trazas **Bar** (Horizontal/Agrupadas) emiten `plotly_selected` al clic; **Pie, Sunburst, Treemap y Funnel solo emiten `plotly_click`**, que Streamlit's `on_select` no escucha — para esas 4 el clic nunca puede filtrar, por más código que se le ponga. El dashboard ahora lo detecta (`es_interactiva`) y muestra un `st.caption` explicando la limitación + sugiriendo cambiar a Bar. Verificado extremo a extremo con clics reales simulados vía CDP (`page.mouse.down/up`, no `.click()` — Plotly necesita el evento nativo con separación mousedown/mouseup, un `force click` de Playwright no siempre lo dispara).
- **Nueva sección "👤 Por Facturador"** (punto 9): radio con 3 vistas — Distribución de Facturas (por `UsuaDigi`), Anulaciones Realizadas (por `UsuaAnul`, incluye motivo real desde el catálogo `CausAnul`) y Liquidaciones Pendientes de Causar (por `UsuaDigi`, `Causado=0`) — cada una con gráfica de barras (con el mismo drill-down por clic) + la tabla agregada visible debajo (antes solo había un expander con TODAS las facturas sin agrupar, que no coincidía con lo que mostraba la gráfica) + tabla de detalle del facturador clicado, descargable.
- **Bug de reconciliación de Streamlit** (hallado verificando el punto 4 en vivo): un `st.caption()` condicional (aparecía solo en la rama "no interactiva") podía quedar huérfano en el DOM al cambiar de tipo de gráfica — el texto de ayuda de una gráfica anterior se quedaba pegado en pantalla aunque el Python de esa corrida nunca lo emitiera (confirmado con un `st.write` de depuración: el condicional era correcto, el DOM no). Persistía incluso reiniciando el server. Solucionado renderizando **siempre** el mismo `st.caption()` en la misma posición y solo cambiando el texto, en vez de incluirlo condicionalmente — evita que Streamlit tenga que reconciliar 0 vs 1 elementos entre corridas. **Lección aparte para depuración futura en este proyecto**: el servidor de desarrollo en Windows no recarga módulos importados (`modules/*.py`) al guardarlos — solo re-ejecuta `app.py`; hay que matar y relanzar `streamlit run app.py` tras cada edición antes de verificar con Playwright, o se prueban versiones obsoletas sin darse cuenta.

### v2.3 (2026-09-11)
- **Corregido bug real** en "Reportes → Admisiones sin Cerrar → Agrupación por área": `get_admisiones_sin_cerrar_por_area()` y `get_admisiones_sin_cerrar_con_cama_por_area()` agrupaban por `Admision.CodiServ` (servicio de **ingreso**, fijo) en vez de `Admision.ServEgre` (servicio **actual**) — el propio docstring ya decía "servicio actual", solo el código estaba mal. Esto hacía que áreas de paso como Urgencias-Observación se vieran casi vacías (1 admisión) cuando en realidad tenían 43. Ver Notas de Schema SIHOS.
- **Corregido truncamiento silencioso** en la tabla/Excel de detalle por área: `get_admisiones_sin_cerrar_detalle_por_servicio()` tenía `LIMIT 1000` fijo — un área con más de 1,000 admisiones abiertas (ej. Ambulatorios, 8,269) se veía y se descargaba incompleta sin ningún aviso. Subido a `LIMIT 20000` (en la práctica, sin tope real para los volúmenes actuales).
- Evaluado si esta vista debería depender del rango de fechas del sidebar — se decidió que no: es un backlog en tiempo real (promedio real ~200-300 días abierta), filtrarlo por fecha de ingreso escondería justo las admisiones más viejas y críticas que hay que cerrar.
- **Corregido segundo bug real** en toda la familia "Admisiones sin Cerrar" (`get_admisiones_sin_cerrar_resumen`, `_detalle`, `_por_area`, `_con_cama_por_area`, `_detalle_por_servicio`): exigían `FechEgre IS NULL` además de `Cerrado=2`. Reportado por el usuario con 2 casos reales de Hosp Gineco-Obstetricia que SIHOS mostraba como abiertas y el dashboard no. Causa: una historia con `Cerrado=2` sigue sin cerrar aunque `FechEgre` ya tenga valor (falta el clic de "Cerrar Historia" — es el mismo caso que "Proceso Incompleto" en Camas Bloqueadas). Se quitó la condición `FechEgre IS NULL` en las 5 queries. Impacto medido: 109 admisiones sin cerrar reales estaban excluidas en todo el dashboard, 54 de ellas invisibles en absolutamente ningún reporte (sin cama real asignada, tampoco salían en Camas Bloqueadas). `get_admisiones_sin_cerrar_por_area` ahora expone `pendientes_cerrar_historia` por área, y `get_admisiones_sin_cerrar_detalle`/`_detalle_por_servicio` exponen `FechEgre` para identificar a simple vista cuáles solo les falta el cierre formal. De paso, `get_admisiones_sin_cerrar_detalle` (la tabla con el slider de días) se corrigió para mostrar servicio **actual** (`ServEgre` + nombre) en vez de servicio de ingreso — mismo bug de v2.3 anterior, se había quedado sin corregir en esta query específica.

- **Mostrar nombre de persona en vez de login SIHOS** en toda columna "usuario" (quién abrió/modificó/cerró una admisión o cama): `get_ocupacion_detalle_camas`, `get_cierres_tardios`, `get_admisiones_sin_cerrar_detalle`, `get_admisiones_sin_cerrar_detalle_por_servicio`, `get_camas_bug_sinergia`, `get_camas_proceso_incompleto` y `get_rda_detalle` seleccionaban directamente el código de login (`Admision.UsuaDigi`/`UsuaModi`, `EnviRda.usuario`) sin cruzar con `Usuarios`. Se añadió `LEFT JOIN Usuarios u ON u.Login = <campo>` + `COALESCE(u.Nombre, <campo>)` en las 7 queries, replicando el patrón que ya usaba `get_camas_detalle()`. Verificado en vivo: 501/501 logins de `Admision` y 311/311 de `EnviRda` cruzan con `Usuarios.Login`, y `Usuarios.Nombre` nunca está vacío (2,147 usuarios) — el fallback al login prácticamente nunca se activa en la práctica.

### v2.2 (2026-09-10)
- Tooltips ⓘ en todas las tarjetas de KPI (`render_metric_card(help_text=...)` / `st.metric(help=...)`) en los 12 módulos con métricas, reemplazando captions/`st.info`/`st.warning` que solo explicaban un KPI puntual.
- Auditado en vivo el filtro `Anulado` de "Admisiones sin Cerrar" y Ocupación: confirmado correcto (`Anulado=2` = válida), no había bug — sí existen 60 admisiones anuladas marcadas como abiertas en el sistema origen, pero el dashboard ya las excluye.
- **Corregido bug real** en `get_produccion_profesional_*` (Actividad Clínica → Producción Individual): usaban códigos de `DetaCita.EstaCita` equivocados (mezclaba estados reales de cita con tipos de slot internos de agenda, código 1=Disponible tratado como "Cumplida"). Verificado y corregido contra la tabla de referencia `EstaCita`.
- Reconectadas temporalmente `modules/profesionales.py` y `modules/citas.py` como pestañas "(comparar)" — pendiente decidir si se fusiona su funcionalidad faltante en `actividad.py` y se eliminan (ver Pendientes / Deuda técnica).
- Documentada la ruta real de despliegue en VPS (`/home/dashboard_sihos`) y el flujo de actualización (`git pull` + `systemctl restart dashboard-sihos`).
- **Corregido bug visual** del tooltip ⓘ (el `?` salía como texto plano pegado al título del KPI), en dos capas: (1) la regla CSS `.metric-help` se había agregado en `assets/components.css`, que nunca se carga — se movió al `<style>` real embebido en `components/layout.py::render_header()`; (2) `.metric-card` tenía `overflow: hidden`, que recortaba el globo del tooltip por salirse del borde de la tarjeta — se quitó y en su lugar se redondea solo la barra de acento superior (`.metric-card::before`). Verificado visualmente con Playwright (captura del tooltip en su punto de opacidad máxima). De paso se descubrió que `assets/*.css` es código muerto en todo el proyecto (ver Pendientes / Deuda técnica).
- **Tooltips ⓘ extendidos a encabezados de gráficas/secciones** (no solo KPIs): nuevos helpers `render_heading_help()` y `render_section_banner(..., help_text=...)` en `components/widgets.py`, con variante `.metric-help-inverse` (insignia blanca translúcida) para verse bien sobre los banners de color. Aplicado a las 13 gráficas/secciones que tenían un `st.caption`/`st.info` fijo explicando metodología (ej. "excluye estancias > 60 días", "Solo estados 1-7", fuente de datos SISMED, leyenda del mapa de calor de seguridad) en `admisiones.py`, `actividad.py`, `citas.py`, `profesionales.py`, `reportes.py` e `inventario.py`. Se dejaron visibles a propósito las alertas dinámicas/activas (ej. "difiere del reporte SIHOS nativo", conteos de camas bloqueadas) — esas no son definiciones de KPI/gráfica, son datos que cambian y ameritan visibilidad permanente.

### v2.1 (2026-04-01)
- Sistema de login con roles (admin, gerencia, calidad)
- Credenciales movidas a `.streamlit/secrets.toml`
- Soporte para conexión por IP pública (VPS)
- `db_connector.py` prioriza `st.secrets` sobre `database.yaml`

### v2.0 (2025-12-30)
- Navegación por tabs
- Arquitectura modular (`modules/`)
- Auto-refresh cada 5 minutos
- Conexión MySQL con `db_connector.py`

---

© 2026 Hospital Regional Alfonso Jaramillo Salazar. Todos los derechos reservados.

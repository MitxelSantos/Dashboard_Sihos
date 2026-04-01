# Dashboard SIHOS

## Hospital Regional Alfonso Jaramillo Salazar
**Sistema de Información Hospitalaria — Líbano, Tolima**

---

## Descripción

Dashboard centralizado en tiempo real para visualización de indicadores hospitalarios. Construido con Streamlit sobre la base de datos MySQL de SIHOS.

---

## Características

- **Login con roles** — admin, gerencia, calidad. Cada rol ve solo las pestañas autorizadas.
- **Credenciales seguras** — ninguna contraseña en el código fuente; todo en `.streamlit/secrets.toml` (excluido de git).
- **Auto-refresh** — actualización automática cada 5 minutos.
- **Módulos independientes** — cada pestaña es un módulo separado en `modules/`.
- **Conexión read-only** a MySQL SIHOS.

---

## Módulos disponibles

| Pestaña | Roles con acceso |
|---|---|
| Home | Todos |
| Admisiones | admin, gerencia |
| Facturación | admin, gerencia |
| Procedimientos | admin, calidad |
| Cirugías | admin, calidad |
| Ocupación | Todos |
| Profesionales | admin, gerencia |
| Consultas SQL | admin |

---

## Estructura del proyecto

```
Dashboard_SIHOS/
├── app.py                        # Entrada principal, login, routing por tabs
├── config/
│   └── settings.py               # PAGE_TITLE, TABS_CONFIG, TAB_ORDER, COLORS
├── modules/                      # Un archivo por pestaña
│   ├── home.py
│   ├── admisiones.py
│   ├── facturacion.py
│   ├── procedimientos.py
│   ├── cirugias.py
│   ├── ocupacion.py
│   ├── profesionales.py
│   └── consultas_sql.py
├── components/
│   ├── layout.py                 # Header, Sidebar, Footer
│   └── widgets.py                # Métricas y componentes reutilizables
├── utils/
│   ├── db_connector.py           # Conexión MySQL (lee de secrets.toml)
│   ├── queries.py                # Queries centralizadas
│   └── charts.py                 # Helpers de gráficas
├── assets/
│   ├── logo.png
│   ├── base.css
│   ├── layout.css
│   └── components.css
└── .streamlit/
    ├── config.toml               # Tema Streamlit (en git)
    └── secrets.toml              # Credenciales (NO en git)
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
admin    = ["home", "admisiones", "facturacion", "procedimientos", "cirugias", "ocupacion", "profesionales", "consultas_sql"]
gerencia = ["home", "admisiones", "facturacion", "ocupacion", "profesionales"]
calidad  = ["home", "procedimientos", "cirugias", "ocupacion"]
```

> Para agregar usuarios o cambiar permisos: edita solo `secrets.toml`, sin tocar código.

---

## Despliegue en VPS (AlmaLinux 8 / WHM)

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
git clone https://github.com/MitxelSantos/Dashboard_Sihos.git /home/hospital/dashboard_sihos
cd /home/hospital/dashboard_sihos
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
```bash
# /etc/systemd/system/dashboard-sihos.service
systemctl enable dashboard-sihos
systemctl start dashboard-sihos
```

### 6. Virtual host Apache (WHM)
Proxy desde el subdominio hacia `127.0.0.1:8501` con soporte WebSocket.

---

## Agregar un nuevo módulo

1. Crear `modules/nuevo_modulo.py` con función `render_nuevo_modulo()`
2. Añadir entrada en `TABS_CONFIG` y `TAB_ORDER` en `config/settings.py`
3. Importar y registrar en `tab_functions` en `app.py`
4. Añadir el key en los roles que deben verlo en `secrets.toml`

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

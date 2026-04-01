"""
Configuración del Dashboard SIHOS
"""
import os

# Información del hospital
HOSPITAL_NAME = "Hospital Regional Alfonso Jaramillo Salazar"
HOSPITAL_SUBTITLE = "Sistema de Información Hospitalaria - Líbano, Tolima"

# Configuración de pestañas
TABS_CONFIG = {
    "home": {
        "name": "Home",
        "icon": "🏠"
    },
    "admisiones": {
        "name": "Admisiones",
        "icon": "🏥"
    },
    "facturacion": {
        "name": "Facturación",
        "icon": "💰"
    },
    "procedimientos": {
        "name": "Procedimientos",
        "icon": "🔬"
    },
    "cirugias": {
        "name": "Cirugías",
        "icon": "⚕️"
    },
    "ocupacion": {
        "name": "Ocupación",
        "icon": "🛏️"
    },
    "profesionales": {
        "name": "Profesionales",
        "icon": "👨‍⚕️"
    },
    "consultas_sql":{
        "name": "consultas_sql",
        "icon": "🖥️"
    }
}

# Orden de las pestañas
TAB_ORDER = [
    "home",
    "admisiones", 
    "facturacion",
    "procedimientos",
    "cirugias",
    "ocupacion",
    "profesionales",
    "consultas_sql"
]

# Colores institucionales
COLORS = {
    'primary': '#2C5F2D',      # Verde institucional
    'secondary': '#97BC62',    # Verde claro
    'success': '#4CAF50',      # Verde éxito
    'info': '#2196F3',         # Azul información
    'warning': '#FF9800',      # Naranja advertencia
    'danger': '#F44336',       # Rojo peligro
    'light': '#F5F5F5',        # Gris claro
    'dark': '#212529'          # Negro
}

# Emojis para métricas
METRIC_EMOJIS = {
    'admisiones': '🏥',
    'activas': '✅',
    'cerradas': '🔒',
    'urgencias': '🚨',
    'hospitalizacion': '🛏️',
    'consulta': '👨‍⚕️',
    'facturacion': '💰',
    'total': '📊',
    'promedio': '📈',
    'maximo': '⬆️',
    'procedimientos': '🔬',
    'cirugias': '⚕️',
    'duracion': '⏱️',
    'anestesia': '💉',
    'ocupacion': '🛏️',
    'camas': '🛏️',
    'libres': '⭕',
    'ocupadas': '✅',
    'profesionales': '👨‍⚕️',
    'atenciones': '📋',
    'pacientes': '👥'
}

# Configuración del dashboard
PAGE_TITLE = "Dashboard HRAJS"
PAGE_ICON = "🏥"
LAYOUT = "wide"

# Logo
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")

# Cache
CACHE_TTL = 300  # 5 minutos

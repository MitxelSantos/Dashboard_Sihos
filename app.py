"""
Dashboard SIHOS - Aplicación Principal
Auto-refresh global cada 5 minutos
"""

import streamlit as st
import time

from config.settings import PAGE_TITLE, PAGE_ICON, LAYOUT, TABS_CONFIG, TAB_ORDER
from components.layout import render_header, render_sidebar, render_footer

# Importar módulos
from modules.home import render_inicio
from modules.admisiones import render_admisiones
from modules.facturacion import render_facturacion
from modules.procedimientos import render_procedimientos
from modules.cirugias import render_cirugias
from modules.ocupacion import render_ocupacion
from modules.profesionales import render_profesionales
from modules.consultas_sql import render_consultas_sql

# ============================================================================
# AUTO-REFRESH GLOBAL - APLICA A TODAS LAS PESTAÑAS
# ============================================================================
# Inicializar timestamp si no existe
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()

# Verificar si han pasado 5 minutos (300 segundos)
tiempo_transcurrido = time.time() - st.session_state.last_update

if tiempo_transcurrido > 300:  # 5 minutos
    st.session_state.last_update = time.time()
    st.rerun()

# Mostrar tiempo hasta próxima actualización (en todas las pestañas)
tiempo_restante = 300 - int(tiempo_transcurrido)
minutos_restantes = tiempo_restante // 60
segundos_restantes = tiempo_restante % 60

# ============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================================
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

# Renderizar header
render_header()

# Renderizar sidebar con filtros
render_sidebar()

# Crear pestañas
tab_labels = [f"{TABS_CONFIG[tab]['icon']} {TABS_CONFIG[tab]['name']}" for tab in TAB_ORDER]
tabs = st.tabs(tab_labels)

# Mapear funciones a pestañas
tab_functions = {
    "home": render_inicio,
    "admisiones": render_admisiones,
    "facturacion": render_facturacion,
    "procedimientos": render_procedimientos,
    "cirugias": render_cirugias,
    "ocupacion": render_ocupacion,
    "profesionales": render_profesionales,
    "consultas_sql": render_consultas_sql
}

# Renderizar contenido de cada pestaña
for idx, tab_key in enumerate(TAB_ORDER):
    with tabs[idx]:
        try:
            render_func = tab_functions[tab_key]
            render_func()
        except Exception as e:
            st.error(f"Error al cargar {TABS_CONFIG[tab_key]['name']}: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

"""
Dashboard SIHOS - Aplicación Principal
Auto-refresh global cada 5 minutos + Sistema de Seguridad Login
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
# CONFIGURACIÓN DE LA PÁGINA (Debe ser lo primero)
# ============================================================================
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

# ============================================================================
# SISTEMA DE LOGIN CON ROLES
# Credenciales y permisos definidos en .streamlit/secrets.toml
# ============================================================================

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_rol' not in st.session_state:
    st.session_state.usuario_rol = None

def _verificar_credenciales(usuario: str, clave: str) -> bool:
    """Verifica usuario/contraseña contra secrets y guarda el rol en session_state."""
    usuarios = st.secrets.get("usuarios", {})
    if usuario in usuarios and usuarios[usuario]["password"] == clave:
        st.session_state.usuario_nombre = usuario
        st.session_state.usuario_rol = usuarios[usuario]["rol"]
        return True
    return False

def _tabs_permitidas() -> list[str]:
    """Devuelve la lista de tab_keys accesibles para el rol activo."""
    rol = st.session_state.usuario_rol
    roles = st.secrets.get("roles", {})
    # admin siempre ve todo aunque no esté en la config
    if rol == "admin":
        return list(TAB_ORDER)
    return [t for t in TAB_ORDER if t in roles.get(rol, [])]

def login():
    """Pantalla de acceso centralizada."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("# 🔐 Acceso al Sistema")
        st.info("Ingresa tus credenciales autorizadas por el hospital para ver el Dashboard.")
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                if _verificar_credenciales(usuario, clave):
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")

# Verificar si el usuario está logueado
if not st.session_state.autenticado:
    login()
    st.stop()  # Detiene la ejecución de todo lo que sigue

# ============================================================================
# AUTO-REFRESH GLOBAL (Solo si ya está autenticado)
# ============================================================================
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()

tiempo_transcurrido = time.time() - st.session_state.last_update

if tiempo_transcurrido > 300:  # 5 minutos
    st.session_state.last_update = time.time()
    st.rerun()

# --- HEADER Y SIDEBAR (Solo visibles tras login) ---
render_header()
render_sidebar()

# Mostrar tiempo restante discretamente en el sidebar
tiempo_restante = 300 - int(tiempo_transcurrido)
st.sidebar.markdown(f"---")
st.sidebar.caption(f"🔄 Próxima actualización en: {tiempo_restante // 60:02d}:{tiempo_restante % 60:02d}")
st.sidebar.markdown(
    f"👤 **{st.session_state.get('usuario_nombre', '')}** "
    f"— `{st.session_state.get('usuario_rol', '')}`"
)
if st.sidebar.button("🔓 Cerrar Sesión"):
    st.session_state.autenticado = False
    st.session_state.usuario_rol = None
    st.rerun()

# ============================================================================
# CONTENIDO DE PESTAÑAS (filtradas por rol)
# ============================================================================
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

tabs_visibles = _tabs_permitidas()
tab_labels = [f"{TABS_CONFIG[tab]['icon']} {TABS_CONFIG[tab]['name']}" for tab in tabs_visibles]
tabs = st.tabs(tab_labels)

for idx, tab_key in enumerate(tabs_visibles):
    with tabs[idx]:
        try:
            tab_functions[tab_key]()
        except Exception as e:
            st.error(f"Error al cargar {TABS_CONFIG[tab_key]['name']}: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
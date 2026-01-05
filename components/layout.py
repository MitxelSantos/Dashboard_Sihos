"""
Componentes de Layout - VERSIÓN RESTAURADA
Con todo el CSS necesario para widgets.py
"""

import streamlit as st
from datetime import datetime, timedelta
import os
import base64
from config.settings import (
    COLORS,
    HOSPITAL_NAME,
    HOSPITAL_SUBTITLE,
    LOGO_PATH
)

def get_logo_base64():
    """Convierte logo a base64 si existe"""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def get_fecha_espanol():
    """Retorna la fecha actual en español sin depender de locale"""
    dias = {
        0: 'Lunes',
        1: 'Martes', 
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo'
    }
    
    meses = {
        1: 'Enero',
        2: 'Febrero',
        3: 'Marzo',
        4: 'Abril',
        5: 'Mayo',
        6: 'Junio',
        7: 'Julio',
        8: 'Agosto',
        9: 'Septiembre',
        10: 'Octubre',
        11: 'Noviembre',
        12: 'Diciembre'
    }
    
    now = datetime.now()
    dia_semana = dias[now.weekday()]  # 0=Lunes, 6=Domingo
    dia = now.day
    mes = meses[now.month]
    año = now.year
    
    return f"{dia_semana}, {dia} de {mes} de {año}"

def render_header():
    """Renderiza el header fijo INTEGRADO con sidebar"""
    
    logo_base64 = get_logo_base64()
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="header-logo" />' if logo_base64 else '<div class="header-logo-placeholder">🏥</div>'
    
    current_date = get_fecha_espanol()
    current_time = datetime.now().strftime("%I:%M %p")
    
    # CSS COMPLETO - Restaurado
    st.markdown(f"""
    <style>
    /* =================================================================
       RESET Y BASE
       ================================================================= */
    :root {{
        --primary: {COLORS['primary']};
        --secondary: {COLORS['secondary']};
        --success: {COLORS['success']};
        --info: {COLORS['info']};
        --warning: {COLORS['warning']};
        --danger: {COLORS['danger']};
        --light: {COLORS['light']};
        --dark: {COLORS['dark']};
        
        --text-primary: #212529;
        --text-secondary: #6c757d;
        --bg-primary: #ffffff;
        --bg-secondary: #f8f9fa;
        --border-color: #dee2e6;
        --card-bg: rgba(255, 255, 255, 0.95);
        
        --shadow-sm: 0 2px 4px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
        --shadow-lg: 0 8px 24px rgba(0,0,0,0.15);
    }}
    
    /* Ocultar header default de Streamlit */
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    
    /* =================================================================
       HEADER PERSONALIZADO - INTEGRADO CON SIDEBAR
       ================================================================= */
    .custom-header {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 115px;
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        z-index: 999;
        display: flex;
        align-items: center;
        padding: 0 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        backdrop-filter: blur(10px);
    }}
    
    .header-content {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        gap: 2rem;
    }}
    
    .header-left {{
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }}
    
    .header-logo {{
        width: 65px;
        height: 65px;
        border-radius: 12px;
        background: white;
        padding: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        object-fit: contain;
    }}
    
    .header-logo-placeholder {{
        width: 65px;
        height: 65px;
        border-radius: 12px;
        background: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }}
    
    .header-text {{
        flex: 1;
    }}
    
    .header-title {{
        color: white !important;
        font-size: 1.75rem;
        font-weight: 800;
        margin: 0;
        padding: 0;
        line-height: 1.1;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        letter-spacing: -0.5px;
    }}
    
    .header-subtitle {{
        color: rgba(255,255,255,0.95);
        font-size: 0.85rem;
        margin: 0.3rem 0 0 0;
        padding: 0;
        line-height: 1.3;
        font-weight: 500;
        text-shadow: 1px 1px 4px rgba(0,0,0,0.2);
    }}
    
    .header-date {{
        color: white;
        font-size: 1rem;
        font-weight: 600;
        text-align: right;
        background: rgba(255,255,255,0.15);
        padding: 0.75rem 1.25rem;
        border-radius: 12px;
        backdrop-filter: blur(10px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        line-height: 1.6;
    }}
    
    /* =================================================================
       SIDEBAR - INTEGRADA CON HEADER
       ================================================================= */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        padding-top: 130px !important;
        box-shadow: 4px 0 20px rgba(0,0,0,0.15);
        z-index: 998 !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown {{
        color: white;
    }}
    
    [data-testid="stSidebar"] h3 {{
        color: white !important;
        font-weight: 700;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
    }}
    
    [data-testid="stSidebar"] label {{
        color: white !important;
        font-weight: 600;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }}
    
    [data-testid="stSidebar"] input {{
        color: #212529 !important;
        background-color: white !important;
        border-radius: 8px;
        border: 2px solid rgba(255,255,255,0.3);
        padding: 0.5rem;
        font-weight: 500;
    }}
    
    [data-testid="stSidebar"] .stDateInput > div {{
        background-color: white;
        border-radius: 8px;
    }}
    
    /* Botón de actualizar en sidebar */
    [data-testid="stSidebar"] .stButton > button {{
        background: white !important;
        color: {COLORS['primary']} !important;
        border: 2px solid white !important;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.75rem 1.5rem;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: {COLORS['primary']} !important;
        color: white !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.25);
    }}
    
    /* =================================================================
       AJUSTE CONTENIDO PRINCIPAL
       ================================================================= */
    .main .block-container {{
        padding-top: 140px !important;
        max-width: 1400px;
    }}
    
    /* =================================================================
       METRIC CARDS - GLASSMORPHISM CON HOVER
       ================================================================= */
    .metric-card {{
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 2rem 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.5);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}
    
    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }}
    
    .metric-card:hover {{
        transform: translateY(-8px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.15);
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.85) 100%);
    }}
    
    .metric-card:hover::before {{
        opacity: 1;
    }}
    
    .metric-icon {{
        font-size: 3.5rem;
        margin-bottom: 0.75rem;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1));
    }}
    
    .metric-label {{
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }}
    
    /* =================================================================
       SECTION BANNER
       ================================================================= */
    .section-banner {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        color: white;
        padding: 1.25rem 2rem;
        border-radius: 15px;
        margin: 2rem 0 1.5rem 0;
        display: flex;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 4px 20px rgba(44, 95, 45, 0.3);
        position: relative;
        overflow: hidden;
    }}
    
    .section-banner::before {{
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: shimmer 3s infinite;
    }}
    
    @keyframes shimmer {{
        0%, 100% {{ transform: translate(0, 0); }}
        50% {{ transform: translate(-20%, -20%); }}
    }}
    
    .section-banner-icon {{
        font-size: 2rem;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
        z-index: 1;
    }}
    
    .section-banner h2 {{
        margin: 0;
        font-size: 1.5rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        z-index: 1;
    }}
    
    /* =================================================================
       SECTION DIVIDER
       ================================================================= */
    .section-divider {{
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, {COLORS['primary']} 50%, transparent 100%);
        border: none;
        margin: 2.5rem 0;
        opacity: 0.3;
    }}
    
    /* =================================================================
       GRADIENT CARD
       ================================================================= */
    .gradient-card {{
        background: linear-gradient(135deg, rgba(44, 95, 45, 0.05) 0%, rgba(151, 188, 98, 0.05) 100%);
        border-radius: 15px;
        padding: 1.5rem;
        border: 1px solid rgba(44, 95, 45, 0.1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    
    /* =================================================================
       TABLAS MEJORADAS
       ================================================================= */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }}
    
    /* =================================================================
       BOTONES MEJORADOS
       ================================================================= */
    .stButton > button {{
        border-radius: 10px;
        font-weight: 600;
        padding: 0.75rem 2rem;
        border: none;
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(44, 95, 45, 0.3);
        transition: all 0.3s ease;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(44, 95, 45, 0.4);
    }}
    
    /* =================================================================
       TABS MEJORADAS
       ================================================================= */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.5rem;
        background: transparent;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background: rgba(255,255,255,0.8);
        border-radius: 12px 12px 0 0;
        padding: 1rem 2rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(255,255,255,0.95);
        transform: translateY(-2px);
    }}
    
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        color: white !important;
        box-shadow: 0 4px 12px rgba(44, 95, 45, 0.3);
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Header HTML
    st.markdown(f"""
    <div class="custom-header">
        <div class="header-content">
            <div class="header-left">
                {logo_html}
                <div class="header-text">
                    <h1 class="header-title">Hospital Regional Alfonso Jaramillo Salazar</h1>
                    <p class="header-subtitle">Sistema de Información Hospitalaria - Líbano, Tolima</p>
                </div>
            </div>
            <div class="header-date">
                Ultima actualización<br>
                📅 {current_date}<br>
                🕐 {current_time}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Renderiza el sidebar con filtros de fecha"""
    
    with st.sidebar:
        # =================================================================
        # FILTROS DE FECHA
        # =================================================================
        st.markdown("### 📅 Filtros de Fecha")
        
        default_end = datetime.now().date()
        default_start = default_end - timedelta(days=30)
        
        fecha_inicio = st.date_input(
            "Fecha Inicio",
            value=default_start,
            key="sidebar_fecha_inicio"
        )
        
        fecha_fin = st.date_input(
            "Fecha Fin",
            value=default_end,
            key="sidebar_fecha_fin"
        )
        
        # Botón de actualizar
        if st.button("🔄 Actualizar Información", use_container_width=True, key="btn_actualizar"):
            st.rerun()

def render_footer():
    """Renderiza el pie de página"""
    st.markdown(f"""
    <style>
    .footer-simple {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        color: white;
        text-align: center;
        padding: 1rem 2rem;
        margin-top: 3rem;
        border-radius: 10px;
        font-size: 0.85rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    </style>
    
    <div class="footer-simple">
        Dashboard SIHOS v1.0 - Desarrollado por Ing. Jose Miguel Santos Naranjo para Hospital Regional Alfonso Jaramillo Salazar - 2026
    </div>
    """, unsafe_allow_html=True)

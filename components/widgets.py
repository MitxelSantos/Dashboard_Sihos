"""
Widgets Components - Componentes Reutilizables
Métricas, banners, cards, etc.
"""

import streamlit as st
import sys
from pathlib import Path

# Agregar path para imports
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import COLORS, METRIC_EMOJIS

# ============================================================================
# MÉTRICAS
# ============================================================================

def render_metric_card(emoji, title, value, color_start=None, color_end=None):
    """
    Renderiza una métrica con estilo moderno
    
    Args:
        emoji: Emoji para la métrica
        title: Título de la métrica
        value: Valor a mostrar
        color_start: Color inicial del gradiente (opcional)
        color_end: Color final del gradiente (opcional)
    """
    if not color_start:
        color_start = COLORS['primary']
    if not color_end:
        color_end = COLORS['secondary']
    
    st.markdown(f"""
<div class="metric-card">
    <div style="text-align: center;">
        <div class="metric-icon">{emoji}</div>
        <div class="metric-label">{title}</div>
        <div style="font-size: 2.5rem; font-weight: 700; color: {color_start};">{value}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SECTION BANNER
# ============================================================================

def render_section_banner(icon, title, fecha_rango=None):
    """
    Renderiza un banner de sección con gradiente
    
    Args:
        icon: Emoji o icono
        title: Título de la sección
        fecha_rango: Rango de fechas opcional (ej: "15 Nov - 15 Dic 2024")
    """
    # Construir HTML del título
    if fecha_rango:
        title_html = f'<h2>{title}</h2><div style="font-size: 0.85rem; color: rgba(255,255,255,0.8); margin-top: -5px;">({fecha_rango})</div>'
    else:
        title_html = f'<h2>{title}</h2>'
    
    # Renderizar banner
    st.markdown(f'''
<div class="section-banner">
    <span class="section-banner-icon">{icon}</span>
    {title_html}
</div>
''', unsafe_allow_html=True)

# ============================================================================
# GRADIENT CARD
# ============================================================================

def render_gradient_card(content_html):
    """
    Renderiza una tarjeta con fondo degradado
    
    Args:
        content_html: Contenido HTML de la tarjeta
    """
    st.markdown(f"""
<div class="gradient-card">
    {content_html}
</div>
""", unsafe_allow_html=True)

# ============================================================================
# INFO BOX
# ============================================================================

def render_info_box(title, content, icon="ℹ️", color="info"):
    """
    Renderiza una caja de información
    
    Args:
        title: Título de la caja
        content: Contenido (puede ser HTML)
        icon: Icono/emoji
        color: Tipo de color (info, success, warning, danger)
    """
    color_value = COLORS.get(color, COLORS['info'])
    
    st.markdown(f"""
<div style="
    background: rgba({color_value}, 0.1);
    border-left: 4px solid {color_value};
    border-radius: 10px;
    padding: 1rem;
    margin: 1rem 0;
">
    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
        <span style="font-size: 1.5rem;">{icon}</span>
        <strong style="font-size: 1.1rem;">{title}</strong>
    </div>
    <div>{content}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# STATS ROW (Fila de Estadísticas)
# ============================================================================

def render_stats_row(stats_list):
    """
    Renderiza una fila de estadísticas
    
    Args:
        stats_list: Lista de diccionarios con {emoji, title, value, color_start, color_end}
    
    Ejemplo:
        render_stats_row([
            {"emoji": "📊", "title": "Total", "value": "1,234", "color_start": "#2D6A4F", "color_end": "#52B788"},
            {"emoji": "✅", "title": "Activos", "value": "890"},
        ])
    """
    cols = st.columns(len(stats_list))
    
    for i, stat in enumerate(stats_list):
        with cols[i]:
            render_metric_card(
                stat.get("emoji", "📊"),
                stat.get("title", "Métrica"),
                stat.get("value", "0"),
                stat.get("color_start"),
                stat.get("color_end")
            )

# ============================================================================
# SECTION DIVIDER (Separador de Sección)
# ============================================================================

def render_section_divider():
    """Renderiza un separador visual entre secciones"""
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ============================================================================
# LOADING MESSAGE
# ============================================================================

def show_loading(message="Cargando datos..."):
    """Muestra un mensaje de carga"""
    with st.spinner(message):
        pass

# ============================================================================
# EMPTY STATE (Estado Vacío)
# ============================================================================

def render_empty_state(icon="📭", title="Sin datos", message="No se encontraron datos para mostrar"):
    """
    Renderiza un estado vacío cuando no hay datos
    
    Args:
        icon: Emoji para el estado vacío
        title: Título del mensaje
        message: Descripción del estado
    """
    st.markdown(f"""
<div style="
    text-align: center;
    padding: 3rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    margin: 2rem 0;
">
    <div style="font-size: 4rem; margin-bottom: 1rem;">{icon}</div>
    <h3 style="color: var(--text-secondary); margin-bottom: 0.5rem;">{title}</h3>
    <p style="color: var(--text-secondary); opacity: 0.8;">{message}</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# QUICK STATS (Estadísticas Rápidas en Lista)
# ============================================================================

def render_quick_stats(stats_dict):
    """
    Renderiza estadísticas rápidas en formato lista
    
    Args:
        stats_dict: Diccionario de estadísticas {título: valor}
    
    Ejemplo:
        render_quick_stats({
            "Total Pacientes": "1,234",
            "Promedio Diario": "45",
            "Máximo Mensual": "67"
        })
    """
    html = '<div style="background: var(--card-bg); padding: 1rem; border-radius: 10px; box-shadow: var(--shadow-md);">'
    
    for title, value in stats_dict.items():
        html += f"""
        <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border-color);">
            <span style="color: var(--text-secondary);">{title}</span>
            <strong style="color: var(--primary);">{value}</strong>
        </div>
        """
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ============================================================================
# BADGE (Etiqueta)
# ============================================================================

def render_badge(text, color="primary", icon=None):
    """
    Renderiza una etiqueta/badge
    
    Args:
        text: Texto del badge
        color: Color del badge (primary, success, warning, danger, info)
        icon: Emoji opcional
    """
    color_value = COLORS.get(color, COLORS['primary'])
    icon_html = f'<span style="margin-right: 0.25rem;">{icon}</span>' if icon else ''
    
    return f"""
<span style="
    background: {color_value};
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.875rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
">
    {icon_html}{text}
</span>
"""

# ============================================================================
# PROGRESS BAR (Barra de Progreso)
# ============================================================================

def render_progress_bar(value, max_value, label="", color="primary", show_percentage=True):
    """
    Renderiza una barra de progreso personalizada
    
    Args:
        value: Valor actual
        max_value: Valor máximo
        label: Etiqueta opcional
        color: Color de la barra
        show_percentage: Mostrar porcentaje
    """
    percentage = (value / max_value * 100) if max_value > 0 else 0
    color_value = COLORS.get(color, COLORS['primary'])
    
    percentage_text = f"{percentage:.1f}%" if show_percentage else ""
    
    st.markdown(f"""
<div style="margin: 1rem 0;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
        <span style="font-weight: 600; color: var(--text-primary);">{label}</span>
        <span style="color: var(--text-secondary);">{value:,} / {max_value:,} {percentage_text}</span>
    </div>
    <div style="
        background: var(--bg-secondary);
        border-radius: 10px;
        height: 20px;
        overflow: hidden;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="
            background: {color_value};
            height: 100%;
            width: {percentage}%;
            border-radius: 10px;
            transition: width 0.3s ease;
        "></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# UTILIDADES DE FECHA
# ============================================================================

def get_fecha_rango_texto(fecha_inicio, fecha_fin):
    """
    Retorna texto sutil con rango de fechas
    Ejemplo: "01-31 Dic 2024" o "15 Nov - 15 Dic 2024"
    """
    from datetime import datetime
    
    meses = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    
    # Convertir a datetime si son strings
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    
    # Formatear
    dia_inicio = fecha_inicio.day
    mes_inicio = meses[fecha_inicio.month]
    dia_fin = fecha_fin.day
    mes_fin = meses[fecha_fin.month]
    año = fecha_fin.year
    
    # Si es el mismo mes
    if fecha_inicio.month == fecha_fin.month and fecha_inicio.year == fecha_fin.year:
        return f"{dia_inicio}-{dia_fin} {mes_fin} {año}"
    # Si es diferente mes pero mismo año
    elif fecha_inicio.year == fecha_fin.year:
        return f"{dia_inicio} {mes_inicio} - {dia_fin} {mes_fin} {año}"
    # Si es diferente año
    else:
        return f"{dia_inicio} {mes_inicio} {fecha_inicio.year} - {dia_fin} {mes_fin} {año}"


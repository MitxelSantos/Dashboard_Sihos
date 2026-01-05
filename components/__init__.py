"""
Paquete de componentes UI para Dashboard SIHOS
"""

from .layout import render_header, render_sidebar, render_footer
from .widgets import render_metric_card, render_section_banner, render_section_divider

__all__ = [
    'render_header',
    'render_sidebar', 
    'render_footer',
    'render_metric_card',
    'render_section_banner',
    'render_section_divider'
]

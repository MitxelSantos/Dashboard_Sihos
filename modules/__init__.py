"""
Paquete de módulos para Dashboard SIHOS
"""

from .home import render_inicio
from .admisiones import render_admisiones
from .facturacion import render_facturacion
from .procedimientos import render_procedimientos
from .cirugias import render_cirugias
from .ocupacion import render_ocupacion
from .profesionales import render_profesionales

__all__ = [
    'render_inicio',
    'render_admisiones',
    'render_facturacion',
    'render_procedimientos',
    'render_cirugias',
    'render_ocupacion',
    'render_profesionales'
]

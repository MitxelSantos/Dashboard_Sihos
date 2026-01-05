"""
Paquete de utilidades para Dashboard SIHOS
"""

from .db_connector import DatabaseConnector, get_db_connector
from .queries import SIHOSQueries

__all__ = [
    'DatabaseConnector',
    'get_db_connector', 
    'SIHOSQueries'
]

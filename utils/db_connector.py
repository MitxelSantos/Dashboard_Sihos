"""
Conector de Base de Datos para SIHOS
Soporta configuración desde database.yaml O sidebar
"""

import mysql.connector
from mysql.connector import Error
import pandas as pd
import streamlit as st
import os
import yaml

class DatabaseConnector:
    """Conector para base de datos MySQL SIHOS"""
    
    def __init__(self, host=None, user=None, password=None, database=None, port=None):
        """Inicializar conector con credenciales"""

        # PRIORIDAD 1: st.secrets [database] (local y VPS — nunca va a git)
        config_from_secrets = self._load_from_secrets()

        if config_from_secrets:
            self.host     = config_from_secrets.get('host', 'localhost')
            self.user     = config_from_secrets.get('user', 'root')
            self.password = config_from_secrets.get('password', '')
            self.database = config_from_secrets.get('database', 'sihos')
            self.port     = config_from_secrets.get('port', 3306)
        else:
            # PRIORIDAD 2: database.yaml (fallback desarrollo local)
            config_from_yaml = self._load_from_yaml()
            if config_from_yaml:
                self.host     = config_from_yaml.get('host', 'localhost')
                self.user     = config_from_yaml.get('user', 'root')
                self.password = config_from_yaml.get('password', '')
                self.database = config_from_yaml.get('database', 'sihos')
                self.port     = config_from_yaml.get('port', 3306)
            else:
                # PRIORIDAD 3: parámetros / sidebar session_state
                self.host     = host or st.session_state.get('sidebar_host', 'localhost')
                self.user     = user or st.session_state.get('sidebar_user', 'root')
                self.password = password or st.session_state.get('sidebar_password', '')
                self.database = database or st.session_state.get('sidebar_database', 'sihos')
                self.port     = port or st.session_state.get('sidebar_puerto', 3306)
        
        self.connection = None
    
    def _load_from_secrets(self):
        """Cargar configuración desde st.secrets [database] si existe."""
        try:
            db = st.secrets.get("database", None)
            if db:
                return dict(db)
        except Exception:
            pass
        return None

    def _load_from_yaml(self):
        """Cargar configuración desde database.yaml"""
        yaml_paths = [
            'database.yaml',           # Raíz del proyecto
            'config/database.yaml',    # En carpeta config
            '../database.yaml',        # Un nivel arriba
        ]
        
        for yaml_path in yaml_paths:
            if os.path.exists(yaml_path):
                try:
                    # IMPORTANTE: Usar UTF-8 para evitar errores de encoding
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        # Retornar la configuración de la base de datos
                        if isinstance(config, dict):
                            # Si tiene estructura anidada (mysql: { host: ... })
                            if 'mysql' in config:
                                return config['mysql']
                            # Si es estructura plana (host: ...)
                            return config
                except Exception as e:
                    st.warning(f"Error leyendo {yaml_path}: {e}")
                    continue
        
        return None
    
    def connect(self):
        """Establecer conexión a la base de datos"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=int(self.port),
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                collation='utf8mb4_general_ci',
                init_command="SET SESSION sql_mode=''"
            )
            return self.connection
        except Error as e:
            st.error(f"Error de conexión: {e}")
            st.info(f"Intentando conectar a: {self.user}@{self.host}:{self.port}/{self.database}")
            return None
    
    def execute_query(self, query, params=None):
        """Ejecutar query y retornar DataFrame"""
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connect()
            
            if self.connection is None:
                return pd.DataFrame()
            
            # Convertir parámetros con nombre a formato MySQL
            if params:
                for key, value in params.items():
                    query = query.replace(f':{key}', f"'{value}'")
            
            df = pd.read_sql(query, self.connection)
            return df
            
        except Error as e:
            st.error(f"Error ejecutando query: {e}")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error general: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Cerrar conexión"""
        if self.connection and self.connection.is_connected():
            self.connection.close()


# Función helper para obtener instancia del conector
def get_db_connector():
    """
    Retorna instancia del conector de base de datos
    NO usa caché para permitir actualización de credenciales
    """
    return DatabaseConnector()

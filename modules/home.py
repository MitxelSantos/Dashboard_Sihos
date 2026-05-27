"""
Módulo Inicio - Vista General del Sistema (DATOS DE HOY)
Resumen ejecutivo de todas las pestañas
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.db_connector import get_db_connector
from utils.queries import SIHOSQueries
from config.settings import COLORS, CACHE_TTL
from components.widgets import (
    render_metric_card,
    render_section_banner,
    render_section_divider
)
from components.layout import render_footer

def render_inicio():
    """Función principal del módulo Inicio"""
    
    # Cargar datos
    @st.cache_data(ttl=300)  # Cache de 5 minutos (sincronizado con auto-refresh)
    def load_inicio_data():
        db = get_db_connector()
        queries = SIHOSQueries()
        data = {}
        try:
            data['admisiones'] = db.execute_query(queries.get_estadisticas_admisiones_hoy())
            data['facturacion'] = db.execute_query(queries.get_facturacion_hoy())
            data['procedimientos'] = db.execute_query(queries.get_procedimientos_hoy())
            data['cirugias'] = db.execute_query(queries.get_cirugias_hoy())
            data['ocupacion'] = db.execute_query(queries.get_ocupacion_actual())
            data['profesionales'] = db.execute_query(queries.get_profesionales_hoy())
            data['rda'] = db.execute_query(queries.get_rda_summary_hoy())
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            return None
        return data
    
    data = load_inicio_data()
    
    if data is None:
        st.error("Error al cargar datos del sistema")
        st.stop()
    
    # =======================================================================
    # ADMISIONES HOY
    # =======================================================================
    render_section_banner("🏥", "Admisiones de Hoy")
    
    if not data['admisiones'].empty:
        adm = data['admisiones'].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_metric_card(
                "📊",
                "ADMISIONES",
                f"{int(adm.get('Total_Admisiones', 0)):,}",
                COLORS['primary'],
                COLORS['secondary']
            )
        
        with col2:
            render_metric_card(
                "✅",
                "ACTIVAS AHORA",
                f"{int(adm.get('Activas', 0)):,}",
                COLORS['success'],
                COLORS['info']
            )
        
        with col3:
            render_metric_card(
                "🚨",
                "URGENCIAS",
                f"{int(adm.get('Urgencias', 0)):,}",
                COLORS['warning'],
                COLORS['danger']
            )
        
        with col4:
            render_metric_card(
                "🛏️",
                "HOSPITALIZACIÓN",
                f"{int(adm.get('Hospitalizacion', 0)):,}",
                COLORS['info'],
                COLORS['primary']
            )
    
    render_section_divider()
    
    # =======================================================================
    # FACTURACIÓN HOY
    # =======================================================================
    render_section_banner("💰", "Facturación de Hoy")
    
    if not data['facturacion'].empty:
        fact = data['facturacion'].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            valor_total = fact.get('Valor_Total', 0) or 0
            render_metric_card(
                "💵",
                "TOTAL FACTURADO",
                f"${int(valor_total):,}",
                COLORS['success'],
                COLORS['info']
            )
            st.caption("*Fuente: DetaFact. Puede diferir del reporte nativo SIHOS (~$800M de brecha conocida).*")

        with col2:
            render_metric_card(
                "📋",
                "FACTURAS",
                f"{int(fact.get('Total_Facturas', 0)):,}",
                COLORS['info'],
                COLORS['primary']
            )
        
        with col3:
            promedio = fact.get('Promedio_Factura', 0) or 0
            render_metric_card(
                "📊",
                "PROMEDIO",
                f"${int(promedio):,}",
                COLORS['primary'],
                COLORS['secondary']
            )
    
    render_section_divider()
    
    # =======================================================================
    # PROCEDIMIENTOS Y CIRUGÍAS HOY
    # =======================================================================
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        render_section_banner("🔬", "Procedimientos Hoy")
        
        if not data['procedimientos'].empty:
            proc = data['procedimientos'].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                render_metric_card(
                    "🔬",
                    "PROCEDIMIENTOS",
                    f"{int(proc.get('Total_Procedimientos', 0)):,}",
                    COLORS['info'],
                    COLORS['primary']
                )
            
            with col2:
                render_metric_card(
                    "🏥",
                    "SERVICIOS USADOS",
                    f"{int(proc.get('Servicios_Activos', 0)):,}",
                    COLORS['success'],
                    COLORS['secondary']
                )
    
    with col_der:
        render_section_banner("⚕️", "Cirugías Hoy")
        
        if not data['cirugias'].empty:
            cir = data['cirugias'].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                render_metric_card(
                    "⚕️",
                    "CIRUGÍAS",
                    f"{int(cir.get('Total_Cirugias', 0)):,}",
                    COLORS['danger'],
                    COLORS['warning']
                )
            
            with col2:
                duracion = cir.get('Duracion_Promedio', 0) or 0
                render_metric_card(
                    "⏱️",
                    "DURACIÓN PROM.",
                    f"{int(duracion)} min",
                    COLORS['warning'],
                    COLORS['info']
                )
    
    render_section_divider()
    
    # =======================================================================
    # OCUPACIÓN Y PROFESIONALES
    # =======================================================================
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        render_section_banner("🛏️", "Ocupación Actual")
        
        if not data['ocupacion'].empty:
            ocup = data['ocupacion'].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                porcentaje = ocup.get('Porcentaje_Ocupacion', 0) or 0
                color = COLORS['danger'] if porcentaje > 80 else COLORS['warning'] if porcentaje > 60 else COLORS['success']
                render_metric_card(
                    "📊",
                    "OCUPACIÓN",
                    f"{porcentaje:.1f}%",
                    color,
                    COLORS['info']
                )
            
            with col2:
                ocupadas = int(ocup.get('Ocupadas', 0))
                total = int(ocup.get('Total_Camas', 0))
                render_metric_card(
                    "🛏️",
                    "CAMAS",
                    f"{ocupadas}/{total}",
                    COLORS['info'],
                    COLORS['primary']
                )
    
    with col_der:
        render_section_banner("👨‍⚕️", "Profesionales Hoy")
        
        if not data['profesionales'].empty:
            prof = data['profesionales'].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                render_metric_card(
                    "📋",
                    "ATENCIONES",
                    f"{int(prof.get('Total_Atenciones', 0)):,}",
                    COLORS['primary'],
                    COLORS['secondary']
                )
            
            with col2:
                render_metric_card(
                    "👨‍⚕️",
                    "MÉDICOS ACTIVOS",
                    f"{int(prof.get('Profesionales_Activos', 0)):,}",
                    COLORS['success'],
                    COLORS['info']
                )
    
    render_section_divider()
    
    # =======================================================================
    # ALERTAS DE OCUPACIÓN
    # =======================================================================
    render_section_banner("🚨", "Alertas de Ocupación por Servicio")
    
    # Cargar alertas
    try:
        db = get_db_connector()
        queries = SIHOSQueries()
        alertas = db.execute_query(queries.get_alertas_ocupacion())
        
        if not alertas.empty:
            for idx, row in alertas.head(10).iterrows():
                porcentaje = row.get('Porcentaje_Ocupacion', 0) or 0
                servicio = row.get('Servicio', 'N/A')
                ocupadas = int(row.get('Ocupadas', 0))
                total = int(row.get('Total_Camas', 0))
                
                # Determinar color según porcentaje
                if porcentaje >= 90:
                    color_inicio = COLORS['danger']
                    color_fin = '#8B0000'
                    icono = "🔴"
                    estado = "CRÍTICO"
                elif porcentaje >= 70:
                    color_inicio = COLORS['warning']
                    color_fin = COLORS['info']
                    icono = "🟡"
                    estado = "ALERTA"
                else:
                    color_inicio = COLORS['success']
                    color_fin = COLORS['secondary']
                    icono = "🟢"
                    estado = "NORMAL"
                
                # Mostrar tarjeta de alerta
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {color_inicio} 0%, {color_fin} 100%);
                    padding: 0.75rem 1rem;
                    border-radius: 10px;
                    margin-bottom: 0.5rem;
                    color: white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 1.5rem; margin-right: 0.5rem;">{icono}</span>
                            <strong>{servicio}</strong>
                            <span style="margin-left: 1rem; font-size: 0.9rem;">({ocupadas}/{total} camas)</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.5rem; font-weight: bold;">{porcentaje:.1f}%</div>
                            <div style="font-size: 0.8rem;">{estado}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay datos de ocupación por servicio disponibles")
    
    except Exception as e:
        st.error(f"Error cargando alertas: {e}")

    render_section_divider()

    # =======================================================================
    # INTEROPERABILIDAD RDA
    # =======================================================================
    render_section_banner("🔗", "Interoperabilidad RDA — Hoy")

    if data.get('rda') is not None and not data['rda'].empty:
        rda = data['rda'].iloc[0]
        total = int(rda.get('Total') or 0) or 1

        enviados   = int(rda.get('Enviados',   0) or 0)
        pendientes = int(rda.get('Pendientes', 0) or 0)
        rechazados = int(rda.get('Rechazados', 0) or 0)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="🟢 Enviados",
                value=f"{enviados:,}",
                delta=f"{enviados / total * 100:.1f}%"
            )
        with col2:
            st.metric(
                label="🟡 Pendientes",
                value=f"{pendientes:,}",
                delta=f"{pendientes / total * 100:.1f}%"
            )
        with col3:
            st.metric(
                label="🔴 Rechazados",
                value=f"{rechazados:,}",
                delta=f"{rechazados / total * 100:.1f}%",
                delta_color="inverse"
            )

        st.caption("Ver detalle completo en la pestaña **📊 Reportes → Interoperabilidad RDA**")
    else:
        st.info("Sin envíos RDA registrados hoy.")

    # Footer
    render_footer()

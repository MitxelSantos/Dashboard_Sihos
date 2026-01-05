"""
Módulo de Consultas SQL Personalizadas
Permite ejecutar consultas SQL ad-hoc sin afectar el rendimiento del dashboard
"""

import streamlit as st
import pandas as pd
from utils.db_connector import get_db_connector
from components.widgets import render_section_banner, render_section_divider
from components.layout import render_footer
from datetime import datetime

def render_consultas_sql():
    """Módulo para ejecutar consultas SQL personalizadas"""
    
    render_section_banner("🔍", "Consultas SQL Personalizadas")
    
    st.markdown("""
    ### 📋 Ejecutor de Consultas SQL
    
    Esta herramienta te permite ejecutar consultas SQL personalizadas sobre la base de datos SIHOS.
    
    **⚠️ Importante:**
    - Solo se permiten consultas SELECT (lectura únicamente)
    - Las consultas están limitadas a 1000 filas
    - Tiempo máximo de ejecución: 30 segundos
    - No uses consultas muy complejas que puedan afectar el rendimiento
    """)
    
    render_section_divider()
    
    # =======================================================================
    # CONSULTAS PREDEFINIDAS
    # =======================================================================
    st.markdown("### 📚 Consultas Predefinidas Útiles")
    
    consultas_predefinidas = {
        "Admisiones de Hoy": """
SELECT 
    a.ConsAdmi,
    a.FechIngr,
    COALESCE(p.NombUsua, a.NumeUsua) as Paciente,
    COALESCE(cs.NombServ, a.CodiServ) as Servicio,
    COALESCE(cc.NombCama, 'Sin Cama') as Cama
FROM Admision a
LEFT JOIN Paciente p ON a.NumeUsua = p.NumeUsua
LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
LEFT JOIN CodiCama cc ON a.ConsAdmi = cc.ConsAdmi
WHERE a.FechIngr = CURDATE()
    AND a.Anulado = 2
ORDER BY a.FechIngr DESC
LIMIT 100;
        """,
        
        "Pacientes Actualmente Hospitalizados": """
SELECT 
    a.ConsAdmi,
    COALESCE(p.NombUsua, a.NumeUsua) as Paciente,
    COALESCE(cs.NombServ, a.CodiServ) as Servicio,
    COALESCE(cc.NombCama, 'Sin Cama') as Cama,
    a.FechIngr,
    DATEDIFF(CURDATE(), a.FechIngr) as Dias_Estancia
FROM Admision a
LEFT JOIN Paciente p ON a.NumeUsua = p.NumeUsua
LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
LEFT JOIN CodiCama cc ON a.ConsAdmi = cc.ConsAdmi
WHERE (a.FechEgre = '0000-00-00' OR a.FechEgre IS NULL)
    AND a.Anulado = 2
ORDER BY Dias_Estancia DESC
LIMIT 100;
        """,
        
        "Cirugías Programadas Hoy": """
SELECT 
    aq.ConsAdmi,
    aq.FechInic,
    aq.HoraInic,
    aq.SalaOper as Quirofano,
    COALESCE(u.Nombre, aq.MediCiru) as Cirujano,
    CASE aq.TipoAnes
        WHEN 1 THEN 'General'
        WHEN 2 THEN 'Regional'
        WHEN 3 THEN 'Local'
        ELSE 'Sin Especificar'
    END as Tipo_Anestesia
FROM ActoQuir aq
LEFT JOIN Usuarios u ON aq.MediCiru = u.Login
WHERE aq.FechInic = CURDATE()
ORDER BY aq.HoraInic
LIMIT 100;
        """,
        
        "Top 20 Medicamentos Más Usados (Último Mes)": """
SELECT 
    COALESCE(cs.NombSumi, hm.CodiMedi) as Medicamento,
    COUNT(*) as Veces_Administrado,
    SUM(hm.Cantidad) as Cantidad_Total
FROM HojaMedi hm
LEFT JOIN CodiSumi cs ON hm.CodiMedi = cs.CodiSumi
WHERE hm.FechMedi >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY hm.CodiMedi, cs.NombSumi
ORDER BY Veces_Administrado DESC
LIMIT 20;
        """,
        
        "Camas Disponibles por Servicio": """
SELECT 
    COALESCE(cs.NombServ, c.CodiServ, 'Sin Servicio') as Servicio,
    COUNT(*) as Total_Camas,
    COUNT(CASE WHEN c.ConsAdmi IS NOT NULL THEN 1 END) as Ocupadas,
    COUNT(CASE WHEN c.ConsAdmi IS NULL THEN 1 END) as Disponibles,
    ROUND((COUNT(CASE WHEN c.ConsAdmi IS NOT NULL THEN 1 END) / COUNT(*)) * 100, 1) as Porcentaje_Ocupacion
FROM CodiCama c
LEFT JOIN CodiServ cs ON c.CodiServ = cs.CodiServ
WHERE c.Activa = 1
GROUP BY c.CodiServ, cs.NombServ
ORDER BY Porcentaje_Ocupacion DESC;
        """,
        
        "Procedimientos Pendientes": """
SELECT 
    hp.ConsAdmi,
    hp.FechProc as Fecha_Programada,
    COALESCE(cs.NombServ, hp.CodiServ) as Servicio,
    COALESCE(cp.NombProc, hp.CodiProc) as Procedimiento,
    DATEDIFF(CURDATE(), hp.FechProc) as Dias_Retraso
FROM HojaProc hp
LEFT JOIN CodiServ cs ON hp.CodiServ = cs.CodiServ
LEFT JOIN CodiProc cp ON hp.CodiProc = cp.CodiProc
WHERE hp.ProcReal = 0
    AND hp.FechProc < CURDATE()
ORDER BY Dias_Retraso DESC
LIMIT 100;
        """,
        
        "Facturación del Mes Actual": """
SELECT 
    DATE(ef.FechFact) as Fecha,
    COUNT(*) as Total_Facturas,
    SUM(ef.ValoTota) as Valor_Total,
    ROUND(AVG(ef.ValoTota), 0) as Promedio_Factura
FROM EncaFact ef
WHERE MONTH(ef.FechFact) = MONTH(CURDATE())
    AND YEAR(ef.FechFact) = YEAR(CURDATE())
    AND ef.Anulado = 0
GROUP BY DATE(ef.FechFact)
ORDER BY Fecha DESC;
        """
    }
    
    consulta_seleccionada = st.selectbox(
        "Selecciona una consulta predefinida:",
        ["-- Escribir consulta personalizada --"] + list(consultas_predefinidas.keys()),
        key="select_consulta_predefinida"
    )
    
    # Si selecciona una predefinida, cargarla en el editor
    if consulta_seleccionada != "-- Escribir consulta personalizada --":
        consulta_inicial = consultas_predefinidas[consulta_seleccionada]
    else:
        consulta_inicial = "-- Escribe tu consulta SQL aquí\nSELECT * FROM Admision LIMIT 10;"
    
    render_section_divider()
    
    # =======================================================================
    # EDITOR DE CONSULTAS
    # =======================================================================
    st.markdown("### ✏️ Editor de Consultas")
    
    consulta_sql = st.text_area(
        "Escribe tu consulta SQL:",
        value=consulta_inicial,
        height=200,
        key="textarea_sql"
    )
    
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        ejecutar = st.button("▶️ Ejecutar", type="primary", use_container_width=True)
    
    with col2:
        limpiar = st.button("🗑️ Limpiar", use_container_width=True)
    
    if limpiar:
        st.rerun()
    
    # =======================================================================
    # EJECUTAR CONSULTA
    # =======================================================================
    if ejecutar:
        # Validaciones de seguridad
        consulta_upper = consulta_sql.strip().upper()
        
        # Solo permitir SELECT
        if not consulta_upper.startswith("SELECT"):
            st.error("⛔ Solo se permiten consultas SELECT")
            st.stop()
        
        # Prohibir palabras peligrosas
        palabras_prohibidas = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
        for palabra in palabras_prohibidas:
            if palabra in consulta_upper:
                st.error(f"⛔ Palabra prohibida detectada: {palabra}")
                st.stop()
        
        # Ejecutar consulta
        try:
            with st.spinner("⏳ Ejecutando consulta..."):
                inicio = datetime.now()
                
                db = get_db_connector()
                
                # Agregar LIMIT automático si no existe
                if "LIMIT" not in consulta_upper:
                    consulta_sql += "\nLIMIT 1000"
                
                resultado = db.execute_query(consulta_sql)
                
                fin = datetime.now()
                tiempo_ejecucion = (fin - inicio).total_seconds()
            
            # Mostrar resultados
            if resultado is not None and not resultado.empty:
                st.success(f"✅ Consulta ejecutada exitosamente en {tiempo_ejecucion:.2f} segundos")
                
                # Métricas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Filas", f"{len(resultado):,}")
                
                with col2:
                    st.metric("Columnas", len(resultado.columns))
                
                with col3:
                    st.metric("Tiempo", f"{tiempo_ejecucion:.2f}s")
                
                # Mostrar datos
                st.markdown("### 📊 Resultados")
                st.dataframe(resultado, use_container_width=True, height=400)
                
                # Exportar a CSV
                csv = resultado.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Descargar CSV",
                    data=csv,
                    file_name=f"consulta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
            else:
                st.warning("⚠️ La consulta no retornó resultados")
                
        except Exception as e:
            st.error(f"❌ Error al ejecutar la consulta:")
            st.code(str(e))
    
    render_section_divider()
    
    # =======================================================================
    # AYUDA Y TIPS
    # =======================================================================
    with st.expander("💡 Tips y Ayuda"):
        st.markdown("""
        ### Consejos para Escribir Consultas
        
        **Tablas Principales:**
        - `Admision` - Admisiones de pacientes
        - `Paciente` - Información de pacientes
        - `ActoQuir` - Cirugías
        - `HojaProc` - Procedimientos
        - `EncaFact` - Facturas
        - `CodiCama` - Camas
        - `CodiServ` - Servicios
        - `Usuarios` - Profesionales
        - `HojaMedi` - Medicamentos administrados
        - `RipsCons` - Consultas médicas
        
        **Campos de Fecha Comunes:**
        - `FechIngr` - Fecha de ingreso (Admision)
        - `FechFact` - Fecha de factura (EncaFact)
        - `FechInic` - Fecha inicio (ActoQuir)
        - `FechProc` - Fecha procedimiento (HojaProc)
        
        **Funciones Útiles:**
        - `CURDATE()` - Fecha actual
        - `DATE_SUB(fecha, INTERVAL n DAY)` - Restar días
        - `COALESCE(campo, 'Default')` - Valor por defecto si es NULL
        - `COUNT(*)` - Contar registros
        - `SUM(campo)` - Sumar valores
        - `AVG(campo)` - Promedio
        
        **Ejemplo de Consulta:**
        ```sql
        SELECT 
            COALESCE(cs.NombServ, 'Sin Servicio') as Servicio,
            COUNT(*) as Total_Admisiones
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE a.FechIngr >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY a.CodiServ, cs.NombServ
        ORDER BY Total_Admisiones DESC;
        ```
        """)
    
    render_footer()

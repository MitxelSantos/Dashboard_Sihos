import streamlit as st
import pandas as pd
from utils.db_connector import get_db_connector
from components.widgets import render_section_banner, render_section_divider
from components.layout import render_footer
from datetime import datetime

def render_consultas_sql():
    """Módulo para ejecutar consultas SQL personalizadas"""
    
    render_section_banner("🔍", "Consultas SQL Personalizadas")
    
    # 1. VALORES INICIALES
    query_default = "-- Escribe tu consulta SQL aquí\nSELECT * FROM Admision LIMIT 10;"

    # 2. INICIALIZAR SESSION STATE
    if 'query_buffer' not in st.session_state:
        st.session_state.query_buffer = query_default

    # 3. DICCIONARIO DE CONSULTAS
    consultas_predefinidas = {
        "Admisiones de Hoy (Detallado)": """
SELECT 
    a.ConsAdmi, 
    a.HoraIngr, 
    COALESCE(p.NombUsua, a.NumeUsua) as Paciente, 
    COALESCE(cs.NombServ, a.CodiServ) as Servicio,
    a.MotiCons as Motivo
FROM Admision a 
LEFT JOIN Paciente p ON a.NumeUsua = p.NumeUsua 
LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ 
WHERE a.FechIngr = CURDATE() 
    AND a.Anulado = 2 
ORDER BY a.HoraIngr DESC
        """,

        "Cirugías Realizadas Hoy": """
SELECT 
    aq.ConsAdmi, 
    aq.HoraInic, 
    aq.HoraFina,
    TIMESTAMPDIFF(MINUTE, CONCAT(aq.FechInic, ' ', aq.HoraInic), CONCAT(aq.FechFina, ' ', aq.HoraFina)) as Minutos,
    aq.DiagPreo as CIE10_Pre,
    aq.DiagPost as CIE10_Post,
    COALESCE(u.Nombre, aq.UsuaDigi) as Registrado_Por
FROM ActoQuir aq 
LEFT JOIN Usuarios u ON aq.UsuaDigi = u.Login 
WHERE aq.FechInic = CURDATE() 
ORDER BY aq.HoraInic ASC
        """,

        "Estado Real de Camas (Ocupación)": """
SELECT 
    COALESCE(cs.NombServ, c.CodiServ) as Servicio, 
    COUNT(*) as Total_Camas, 
    SUM(CASE WHEN c.ConsAdmi <> '' AND c.ConsAdmi IS NOT NULL THEN 1 ELSE 0 END) as Ocupadas, 
    SUM(CASE WHEN c.ConsAdmi = '' OR c.ConsAdmi IS NULL THEN 1 ELSE 0 END) as Disponibles,
    ROUND((SUM(CASE WHEN c.ConsAdmi <> '' AND c.ConsAdmi IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*)) * 100, 1) as Porcentaje
FROM CodiCama c 
LEFT JOIN CodiServ cs ON c.CodiServ = cs.CodiServ 
WHERE c.Activa = 1 
GROUP BY c.CodiServ, cs.NombServ 
ORDER BY Porcentaje DESC
        """,

        "Medicamentos Administrados (Últimas 24h)": """
SELECT 
    hm.HoraMedi,
    COALESCE(cs.NombSumi, hm.CodiMedi) as Medicamento, 
    hm.CantMedi as Cantidad,
    hm.ConsAdmi as Admision,
    u.Nombre as Enfermera_Asis
FROM HojaMedi hm 
LEFT JOIN CodiSumi cs ON hm.CodiMedi = cs.CodiSumi 
LEFT JOIN Usuarios u ON hm.UsuaDigi = u.Login
WHERE hm.FechMedi = CURDATE() 
ORDER BY hm.HoraMedi DESC
        """,

        "Pacientes con Estancia Prolongada (> 10 días)": """
SELECT 
    a.ConsAdmi, 
    COALESCE(p.NombUsua, a.NumeUsua) as Paciente, 
    a.FechIngr, 
    DATEDIFF(CURDATE(), a.FechIngr) as Dias_Estancia,
    COALESCE(cs.NombServ, a.CodiServ) as Servicio
FROM Admision a 
LEFT JOIN Paciente p ON a.NumeUsua = p.NumeUsua 
LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ 
WHERE (a.FechEgre IS NULL OR a.FechEgre = '0000-00-00') 
    AND a.Anulado = 2
    AND DATEDIFF(CURDATE(), a.FechIngr) > 10
ORDER BY Dias_Estancia DESC
        """,

        "Auditoría: Diagnósticos de Ingreso (Hoy)": """
SELECT 
    a.DiagIngr as CIE10,
    COUNT(*) as Cantidad
FROM Admision a
WHERE a.FechIngr = CURDATE() AND a.Anulado = 2
GROUP BY a.DiagIngr
ORDER BY Cantidad DESC
        """,

        "Camas por Estado Detallado": """
SELECT 
    Estado,
    COUNT(*) as Cantidad
FROM CodiCama
WHERE Activa = 1
GROUP BY Estado
ORDER BY Cantidad DESC
        """
    }

    # 4. CALLBACKS PARA CONTROLAR EL FLUJO
    def al_cambiar_selector():
        if st.session_state.selector_sql != "-- Escribir consulta personalizada --":
            st.session_state.query_buffer = consultas_predefinidas[st.session_state.selector_sql]

    def al_limpiar():
        st.session_state.query_buffer = query_default
        st.session_state.selector_sql = "-- Escribir consulta personalizada --"
        # No usamos rerun aquí para evitar el error de instanciación, el cambio de estado basta

    # 5. INTERFAZ: SELECTOR
    st.selectbox(
        "Selecciona una consulta predefinida:",
        ["-- Escribir consulta personalizada --"] + list(consultas_predefinidas.keys()),
        key="selector_sql",
        on_change=al_cambiar_selector
    )

    render_section_divider()

    # 6. INTERFAZ: EDITOR (IMPORTANTE: Sin 'value' vinculado directamente a key si queremos control total)
    # Usamos st.text_area con el valor del buffer actual
    consulta_sql = st.text_area(
        "Editor SQL:",
        value=st.session_state.query_buffer,
        height=200,
        help="Puedes editar la consulta seleccionada o escribir una nueva."
    )
    
    # Actualizamos el buffer con lo que el usuario escribe para no perder cambios al dar 'Ejecutar'
    st.session_state.query_buffer = consulta_sql

    col1, col2, _ = st.columns([1, 1, 3])
    with col1:
        ejecutar = st.button("▶️ Ejecutar", type="primary", use_container_width=True)
    with col2:
        # El botón limpiar ahora llama al callback que resetea las variables
        st.button("🗑️ Limpiar", on_click=al_limpiar, use_container_width=True)

    # 7. LÓGICA DE EJECUCIÓN
    if ejecutar:
        if not consulta_sql.strip().upper().startswith("SELECT"):
            st.error("Solo se permiten consultas SELECT.")
        else:
            try:
                with st.spinner("Procesando..."):
                    db = get_db_connector()
                    # Asegurar LIMIT de seguridad
                    query_to_run = consulta_sql if "LIMIT" in consulta_sql.upper() else consulta_sql + " LIMIT 1000"
                    df = db.execute_query(query_to_run)
                    
                    if df is not None and not df.empty:
                        st.dataframe(df, use_container_width=True)
                        st.download_button("Descargar resultados", df.to_csv(index=False), "query.csv")
                    else:
                        st.info("La consulta no devolvió resultados.")
            except Exception as e:
                st.error(f"Error: {e}")

    render_footer()
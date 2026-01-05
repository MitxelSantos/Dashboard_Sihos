"""
SIHOS Queries - VERSIÓN FINAL
Sin límites, con todos los campos, corregidas
"""

class SIHOSQueries:
    
    # ========================================================================
    # ADMISIONES
    # ========================================================================
    
    def get_estadisticas_admisiones_hoy(self):
        """Estadísticas del día actual"""
        return """
        SELECT 
            COUNT(*) as Total_Admisiones,
            COUNT(CASE WHEN Cerrado = 2 THEN 1 END) as Activas,
            COUNT(CASE WHEN Cerrado = 1 THEN 1 END) as Cerradas,
            COUNT(CASE WHEN TipoAten = 1 THEN 1 END) as Urgencias,
            COUNT(CASE WHEN TipoAten = 2 THEN 1 END) as Hospitalizacion,
            COUNT(CASE WHEN TipoAten = 3 THEN 1 END) as Consulta_Externa
        FROM Admision
        WHERE DATE(FechIngr) = CURDATE()
            AND Anulado = 2
        """
    
    def get_admisiones_por_fecha(self, fecha_inicio, fecha_fin):
        """Admisiones - SIN LÍMITE"""
        return f"""
        SELECT 
            a.ConsAdmi as Consecutivo,
            a.FechIngr as Fecha_Ingreso,
            DATE_FORMAT(a.HoraIngr, '%H:%i') as Hora,
            a.NumeUsua as Documento,
            COALESCE(cs.NombServ, a.CodiServ) as Servicio,
            CASE 
                WHEN a.TipoAten = 1 THEN 'Urgencias'
                WHEN a.TipoAten = 2 THEN 'Hospitalización'
                WHEN a.TipoAten = 3 THEN 'Consulta Externa'
                WHEN a.TipoAten = 4 THEN 'Otro'
                ELSE CONCAT('Tipo ', a.TipoAten)
            END as Tipo_Atencion,
            CASE 
                WHEN a.Cerrado = 1 THEN 'Cerrada'
                WHEN a.Cerrado = 2 THEN 'Activa'
                ELSE 'Otro'
            END as Estado,
            a.DiagIngr as Diagnostico,
            DATEDIFF(COALESCE(a.FechEgre, CURDATE()), a.FechIngr) as Dias_Estancia
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE a.FechIngr >= '{fecha_inicio}'
            AND a.FechIngr <= '{fecha_fin}'
            AND a.Anulado = 2
        ORDER BY a.FechIngr DESC, a.HoraIngr DESC
        """
    
    def get_admisiones_activas(self):
        """Admisiones activas"""
        return """
        SELECT 
            a.ConsAdmi as Consecutivo,
            a.FechIngr as Fecha_Ingreso,
            a.NumeUsua as Documento,
            COALESCE(cs.NombServ, a.CodiServ) as Servicio,
            CASE 
                WHEN a.TipoAten = 1 THEN 'Urgencias'
                WHEN a.TipoAten = 2 THEN 'Hospitalización'
                WHEN a.TipoAten = 3 THEN 'Consulta Externa'
                ELSE 'Otro'
            END as Tipo_Atencion,
            a.DiagIngr as Diagnostico,
            DATEDIFF(CURDATE(), a.FechIngr) as Dias_Estancia
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE a.Cerrado = 2 AND a.Anulado = 2
        ORDER BY a.FechIngr DESC
        """
    
    def get_admisiones_por_servicio(self):
        """Por servicio - CON PROMEDIO_ESTANCIA"""
        return """
        SELECT 
            COALESCE(cs.NombServ, a.CodiServ) as Servicio,
            COUNT(*) as Total_Admisiones,
            COUNT(CASE WHEN a.Cerrado = 2 THEN 1 END) as Activas,
            COUNT(CASE WHEN a.Cerrado = 1 THEN 1 END) as Cerradas,
            COUNT(CASE WHEN a.TipoAten = 1 THEN 1 END) as Urgencias,
            COUNT(CASE WHEN a.TipoAten = 2 THEN 1 END) as Hospitalizacion,
            ROUND(AVG(DATEDIFF(COALESCE(a.FechEgre, CURDATE()), a.FechIngr)), 1) as Promedio_Estancia
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE a.Anulado = 2
            AND a.FechIngr >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY cs.NombServ, a.CodiServ
        ORDER BY Total_Admisiones DESC
        """
    
    # ========================================================================
    # FACTURACIÓN
    # ========================================================================
    
    def get_facturacion_por_periodo(self, fecha_inicio, fecha_fin):
        """Facturación por periodo"""
        return f"""
        SELECT 
            FechFact as Fecha,
            COUNT(*) as Total_Facturas,
            SUM(ValoTota) as Valor_Total,
            AVG(ValoTota) as Promedio_Factura,
            MAX(ValoTota) as Maximo
        FROM EncaFact
        WHERE Anulado = 0
            AND FechFact >= '{fecha_inicio}'
            AND FechFact <= '{fecha_fin}'
        GROUP BY FechFact
        ORDER BY FechFact DESC
        """
    
    def get_facturacion_por_rango(self):
        """Por rangos - CON PROMEDIO"""
        return """
        SELECT 
            CASE 
                WHEN ValoTota < 100000 THEN 'Menos de 100K'
                WHEN ValoTota < 500000 THEN '100K - 500K'
                WHEN ValoTota < 1000000 THEN '500K - 1M'
                WHEN ValoTota < 5000000 THEN '1M - 5M'
                WHEN ValoTota < 10000000 THEN '5M - 10M'
                ELSE 'Más de 10M'
            END as Rango_Valor,
            COUNT(*) as Cantidad_Facturas,
            SUM(ValoTota) as Valor_Total,
            ROUND(AVG(ValoTota), 0) as Promedio
        FROM EncaFact
        WHERE FechFact >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND Anulado = 0 AND ValoTota > 0
        GROUP BY Rango_Valor
        ORDER BY Cantidad_Facturas DESC
        """
    
    def get_top_facturas(self, limite=15):
        """Top facturas"""
        return f"""
        SELECT 
            NumeFact as Numero_Factura,
            FechFact as Fecha,
            ValoTota as Valor_Total,
            ConsAdmi as Consecutivo_Admision
        FROM EncaFact
        WHERE FechFact >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND Anulado = 0 AND ValoTota > 0
        ORDER BY ValoTota DESC
        LIMIT {limite}
        """
    
    # ========================================================================
    # PROCEDIMIENTOS
    # ========================================================================
    
    def get_procedimientos_por_fecha(self, fecha_inicio, fecha_fin):
        """Procedimientos - SIN LÍMITE"""
        return f"""
        SELECT 
            hp.ConsAdmi as Consecutivo_Admision,
            hp.FechProc as Fecha_Procedimiento,
            DATE_FORMAT(hp.HoraProc, '%H:%i') as Hora,
            hp.CodiProc as Codigo_Procedimiento,
            COALESCE(cs.NombServ, hp.CodiServ) as Servicio,
            hp.DiagPrin as Diagnostico_Principal
        FROM HojaProc hp
        LEFT JOIN CodiServ cs ON hp.CodiServ = cs.CodiServ
        WHERE hp.FechProc >= '{fecha_inicio}'
            AND hp.FechProc <= '{fecha_fin}'
        ORDER BY hp.FechProc DESC, hp.HoraProc DESC
        """
    
    def get_procedimientos_por_admision(self, cons_admi):
        """Procedimientos de admisión"""
        return f"""
        SELECT 
            hp.ConsHoPr as No_Procedimiento,
            hp.FechProc as Fecha,
            DATE_FORMAT(hp.HoraProc, '%H:%i') as Hora,
            hp.CodiProc as Codigo
        FROM HojaProc hp
        WHERE hp.ConsAdmi = '{cons_admi}'
        ORDER BY hp.FechProc DESC
        """
    
    # ========================================================================
    # CIRUGÍAS
    # ========================================================================
    
    def get_cirugias_por_fecha(self, fecha_inicio, fecha_fin):
        """Cirugías - SIN LÍMITE"""
        return f"""
        SELECT 
            aq.ConsAdmi as Consecutivo_Admision,
            aq.NumeActo as No_Acto,
            aq.FechInic as Fecha_Inicio,
            DATE_FORMAT(aq.HoraInic, '%H:%i') as Hora_Inicio,
            aq.FechFina as Fecha_Fin,
            DATE_FORMAT(aq.HoraFina, '%H:%i') as Hora_Fin,
            CASE 
                WHEN aq.TipoAnes = 1 THEN 'General'
                WHEN aq.TipoAnes = 2 THEN 'Regional'
                WHEN aq.TipoAnes = 3 THEN 'Local'
                WHEN aq.TipoAnes = 4 THEN 'Sedación'
                ELSE CONCAT('Tipo ', aq.TipoAnes)
            END as Tipo_Anestesia,
            aq.DiagPreo as Diagnostico_Preoperatorio,
            aq.DiagPost as Diagnostico_Postoperatorio,
            TIMESTAMPDIFF(MINUTE, 
                CONCAT(aq.FechInic, ' ', aq.HoraInic),
                CONCAT(aq.FechFina, ' ', aq.HoraFina)
            ) as Duracion_Minutos
        FROM ActoQuir aq
        WHERE aq.FechInic >= '{fecha_inicio}'
            AND aq.FechInic <= '{fecha_fin}'
        ORDER BY aq.FechInic DESC, aq.HoraInic DESC
        """
    
    def get_cirugias_por_admision(self, cons_admi):
        """Cirugías de admisión"""
        return f"""
        SELECT 
            aq.NumeActo as No_Acto,
            aq.FechInic as Fecha_Inicio,
            DATE_FORMAT(aq.HoraInic, '%H:%i') as Hora_Inicio,
            aq.FechFina as Fecha_Fin,
            DATE_FORMAT(aq.HoraFina, '%H:%i') as Hora_Fin,
            CASE 
                WHEN aq.TipoAnes = 1 THEN 'General'
                WHEN aq.TipoAnes = 2 THEN 'Regional'
                WHEN aq.TipoAnes = 3 THEN 'Local'
                WHEN aq.TipoAnes = 4 THEN 'Sedación'
                ELSE 'Sin especificar'
            END as Tipo_Anestesia,
            aq.DiagPreo as Diag_Preoperatorio,
            aq.DiagPost as Diag_Postoperatorio,
            TIMESTAMPDIFF(MINUTE, 
                CONCAT(aq.FechInic, ' ', aq.HoraInic),
                CONCAT(aq.FechFina, ' ', aq.HoraFina)
            ) as Duracion_Minutos
        FROM ActoQuir aq
        WHERE aq.ConsAdmi = '{cons_admi}'
        ORDER BY aq.FechInic DESC
        """
    
    # ========================================================================
    # OCUPACIÓN HOSPITALARIA
    # ========================================================================
    
    def get_ocupacion_camas(self):
        """Ocupación de camas por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, c.CodiServ) as Servicio,
            COUNT(*) as Total_Camas,
            COUNT(CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 1 END) as Ocupadas,
            COUNT(CASE WHEN c.ConsAdmi IS NULL OR c.ConsAdmi = '' THEN 1 END) as Libres,
            ROUND((COUNT(CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 1 END) / COUNT(*)) * 100, 1) as Porcentaje_Ocupacion
        FROM CodiCama c
        LEFT JOIN CodiServ cs ON c.CodiServ = cs.CodiServ
        WHERE c.Activa = 1
        GROUP BY cs.NombServ, c.CodiServ
        ORDER BY Total_Camas DESC
        """
    
    def get_detalle_camas(self):
        """Detalle de todas las camas"""
        return """
        SELECT 
            c.CodiCama as Codigo,
            c.NombCama as Nombre,
            COALESCE(cs.NombServ, c.CodiServ) as Servicio,
            CASE 
                WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 'Ocupada'
                ELSE 'Libre'
            END as Estado,
            c.ConsAdmi as Admision_Actual,
            CASE WHEN c.EsUci = 1 THEN 'Sí' ELSE 'No' END as Es_UCI
        FROM CodiCama c
        LEFT JOIN CodiServ cs ON c.CodiServ = cs.CodiServ
        WHERE c.Activa = 1
        ORDER BY c.CodiServ, c.CodiCama
        """
    
    # ========================================================================
    # PROFESIONALES
    # ========================================================================
    
    def get_profesionales_atenciones_hoy(self):
        """Atenciones por profesional HOY"""
        return """
        SELECT 
            rc.UsuaCons as Codigo_Profesional,
            COUNT(*) as Total_Atenciones,
            COUNT(CASE WHEN rc.EstaReal = 1 THEN 1 END) as Realizadas,
            COUNT(CASE WHEN rc.EstaReal = 0 THEN 1 END) as Pendientes,
            MIN(DATE_FORMAT(rc.HoraCons, '%H:%i')) as Primera_Atencion,
            MAX(DATE_FORMAT(rc.HoraCons, '%H:%i')) as Ultima_Atencion
        FROM RipsCons rc
        WHERE rc.FechCons = CURDATE()
            AND rc.UsuaCons IS NOT NULL
            AND rc.UsuaCons != ''
        GROUP BY rc.UsuaCons
        ORDER BY Total_Atenciones DESC
        """
    
    def get_profesionales_atenciones_periodo(self, fecha_inicio, fecha_fin):
        """Atenciones por profesional en periodo"""
        return f"""
        SELECT 
            rc.UsuaCons as Codigo_Profesional,
            COUNT(*) as Total_Atenciones,
            COUNT(DISTINCT rc.ConsAdmi) as Pacientes_Unicos,
            COUNT(CASE WHEN rc.EstaReal = 1 THEN 1 END) as Realizadas,
            COUNT(CASE WHEN rc.EstaReal = 0 THEN 1 END) as Pendientes
        FROM RipsCons rc
        WHERE rc.FechCons >= '{fecha_inicio}'
            AND rc.FechCons <= '{fecha_fin}'
            AND rc.UsuaCons IS NOT NULL
            AND rc.UsuaCons != ''
        GROUP BY rc.UsuaCons
        ORDER BY Total_Atenciones DESC
        """
    
    # ========================================================================
    # HISTORIA CLÍNICA (CON MEDICAMENTOS)
    # ========================================================================
    
    def get_admision_by_consecutivo(self, cons_admi):
        """Información de admisión"""
        return f"""
        SELECT 
            a.ConsAdmi as Consecutivo,
            a.NumeUsua as Documento,
            a.FechIngr as Fecha_Ingreso,
            DATE_FORMAT(a.HoraIngr, '%H:%i') as Hora_Ingreso,
            a.FechEgre as Fecha_Egreso,
            COALESCE(cs.NombServ, a.CodiServ) as Servicio,
            a.DiagIngr as Diagnostico_Ingreso,
            CASE 
                WHEN a.Cerrado = 1 THEN 'Cerrada'
                WHEN a.Cerrado = 2 THEN 'Activa'
                ELSE 'Otro'
            END as Estado,
            DATEDIFF(COALESCE(a.FechEgre, CURDATE()), a.FechIngr) as Dias_Estancia
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE a.ConsAdmi = '{cons_admi}'
        """
    
    def get_evoluciones_por_admision(self, cons_admi):
        """Evoluciones"""
        return f"""
        SELECT 
            ev.ConsEvol as No_Evolucion,
            ev.FechEvol as Fecha,
            DATE_FORMAT(ev.HoraEvol, '%H:%i') as Hora,
            ev.Subjetivo as Subjetivo,
            ev.Objetivo as Objetivo,
            ev.Analisis as Analisis,
            ev.PlanMane as Plan_Manejo
        FROM EvolInte ev
        WHERE ev.ConsAdmi = '{cons_admi}'
        ORDER BY ev.FechEvol DESC, ev.HoraEvol DESC
        LIMIT 20
        """
    
    def get_signos_vitales(self, cons_admi, limite=10):
        """Signos vitales"""
        return f"""
        SELECT 
            sv.ConsSign as No_Registro,
            sv.FechToma as Fecha,
            DATE_FORMAT(sv.HoraToma, '%H:%i') as Hora,
            CONCAT(sv.PANume, '/', sv.PADeno) as Presion_Arterial,
            sv.Temperat as Temperatura,
            sv.Pulso as Pulso,
            sv.Respirac as Respiracion
        FROM SignVita sv
        WHERE sv.ConsAdmi = '{cons_admi}'
        ORDER BY sv.FechToma DESC, sv.HoraToma DESC
        LIMIT {limite}
        """
    
    def get_medicamentos_por_admision_simple(self, cons_admi):
        """Medicamentos por admisión - SIMPLE Y RÁPIDO"""
        return f"""
        SELECT 
            ep.ConsPres as No_Prescripcion,
            DATE_FORMAT(ep.Fecha, '%Y-%m-%d') as Fecha,
            DATE_FORMAT(ep.Hora, '%H:%i') as Hora,
            dp.CodiSumi as Codigo_Medicamento,
            dp.CantSumi as Cantidad
        FROM EncaPres ep
        INNER JOIN DetaPres dp 
            ON ep.ConsAdmi = dp.ConsAdmi 
            AND ep.ConsPres = dp.ConsPres
        WHERE ep.ConsAdmi = '{cons_admi}'
        ORDER BY ep.Fecha DESC, ep.Hora DESC
        LIMIT 50
        """

    # ========================================================================
    # QUERIES PARA INICIO - DATOS DE HOY
    # ========================================================================
    
    def get_facturacion_hoy(self):
        """Facturación del día actual"""
        return """
        SELECT 
            COUNT(*) as Total_Facturas,
            SUM(ValoTota) as Valor_Total,
            AVG(ValoTota) as Promedio_Factura,
            MAX(ValoTota) as Factura_Mayor
        FROM EncaFact
        WHERE DATE(FechFact) = CURDATE()
            AND Anulado = 0
            AND ValoTota > 0
        """
    
    def get_procedimientos_hoy(self):
        """Procedimientos del día actual"""
        return """
        SELECT 
            COUNT(*) as Total_Procedimientos,
            COUNT(DISTINCT hp.CodiServ) as Servicios_Activos,
            COUNT(DISTINCT hp.ConsAdmi) as Pacientes_Atendidos
        FROM HojaProc hp
        WHERE DATE(hp.FechProc) = CURDATE()
        """
    
    def get_cirugias_hoy(self):
        """Cirugías del día actual"""
        return """
        SELECT 
            COUNT(*) as Total_Cirugias,
            AVG(TIMESTAMPDIFF(MINUTE, 
                CONCAT(aq.FechInic, ' ', aq.HoraInic),
                CONCAT(aq.FechFina, ' ', aq.HoraFina)
            )) as Duracion_Promedio,
            COUNT(CASE WHEN aq.TipoAnes = 1 THEN 1 END) as Anestesia_General,
            COUNT(CASE WHEN aq.TipoAnes = 2 THEN 1 END) as Anestesia_Regional
        FROM ActoQuir aq
        WHERE DATE(aq.FechInic) = CURDATE()
        """
    
    def get_ocupacion_actual(self):
        """Ocupación actual de camas"""
        return """
        SELECT 
            COUNT(*) as Total_Camas,
            COUNT(CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 1 END) as Ocupadas,
            COUNT(CASE WHEN c.ConsAdmi IS NULL OR c.ConsAdmi = '' THEN 1 END) as Libres,
            ROUND((COUNT(CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 1 END) / COUNT(*)) * 100, 1) as Porcentaje_Ocupacion
        FROM CodiCama c
        WHERE c.Activa = 1
        """
    
    def get_profesionales_hoy(self):
        """Atenciones de profesionales hoy"""
        return """
        SELECT 
            COUNT(*) as Total_Atenciones,
            COUNT(DISTINCT rc.UsuaCons) as Profesionales_Activos,
            COUNT(CASE WHEN rc.EstaReal = 1 THEN 1 END) as Atenciones_Realizadas,
            COUNT(CASE WHEN rc.EstaReal = 0 THEN 1 END) as Atenciones_Pendientes
        FROM RipsCons rc
        WHERE DATE(rc.FechCons) = CURDATE()
            AND rc.UsuaCons IS NOT NULL
            AND rc.UsuaCons != ''
        """

    # ========================================================================
    # NUEVAS QUERIES - ADMISIONES MEJORADAS
    # ========================================================================
    
    def get_tendencia_semanal_admisiones(self):
        """Tendencia de admisiones últimos 7 días"""
        return """
        SELECT 
            DATE(FechIngr) as Fecha,
            COUNT(*) as Total_Admisiones,
            COUNT(CASE WHEN TipoAten = 1 THEN 1 END) as Urgencias,
            COUNT(CASE WHEN TipoAten = 2 THEN 1 END) as Hospitalizacion
        FROM Admision
        WHERE FechIngr >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            AND FechIngr <= CURDATE()
        GROUP BY DATE(FechIngr)
        ORDER BY Fecha
        """
    
    def get_top_diagnosticos_ingreso(self):
        """Top 10 diagnósticos de ingreso más frecuentes"""
        return """
        SELECT 
            DiagIngr as Codigo,
            COUNT(*) as Total
        FROM Admision
        WHERE DiagIngr IS NOT NULL 
            AND DiagIngr != ''
            AND FechIngr >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY DiagIngr
        ORDER BY Total DESC
        LIMIT 10
        """
    
    def get_tiempos_estancia(self):
        """Distribución de tiempos de estancia para hospitalización"""
        return """
        SELECT 
            CASE 
                WHEN DATEDIFF(FechEgre, FechIngr) = 0 THEN '1 día o menos'
                WHEN DATEDIFF(FechEgre, FechIngr) = 1 THEN '1-2 días'
                WHEN DATEDIFF(FechEgre, FechIngr) >= 2 THEN 'Más de 2 días'
            END as Rango,
            COUNT(*) as Total
        FROM Admision
        WHERE TipoAten = 2
            AND FechEgre IS NOT NULL 
            AND FechEgre != '0000-00-00'
            AND FechIngr >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY Rango
        ORDER BY 
            CASE Rango
                WHEN '1 día o menos' THEN 1
                WHEN '1-2 días' THEN 2
                WHEN 'Más de 2 días' THEN 3
            END
        """

    # ========================================================================
    # NUEVAS QUERIES - FACTURACIÓN MEJORADAS
    # ========================================================================
    
    def get_facturacion_por_tipo_afiliacion(self):
        """Facturación distribuida por tipo de afiliación"""
        return """
        SELECT 
            COALESCE(ta.NombTipo, 'Sin Definir') as Tipo,
            COUNT(*) as Total_Facturas,
            SUM(ef.ValoTota) as Valor_Total
        FROM EncaFact ef
        LEFT JOIN TipoAfil ta ON ef.TipoAfil = ta.CodiTipo
        WHERE ef.FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND ef.Anulado = 0
        GROUP BY ef.TipoAfil, ta.NombTipo
        ORDER BY Valor_Total DESC
        """
    
    def get_facturacion_por_servicio(self):
        """Facturación distribuida por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, ef.CodiServ, 'Sin Definir') as Servicio,
            COUNT(*) as Total_Facturas,
            SUM(ef.ValoTota) as Valor_Total
        FROM EncaFact ef
        LEFT JOIN CodiServ cs ON ef.CodiServ = cs.CodiServ
        WHERE ef.FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND ef.Anulado = 0
            AND ef.CodiServ IS NOT NULL
            AND ef.CodiServ != ''
        GROUP BY ef.CodiServ, cs.NombServ
        ORDER BY Valor_Total DESC
        LIMIT 10
        """

    # ========================================================================
    # NUEVAS QUERIES - PROCEDIMIENTOS MEJORADOS
    # ========================================================================
    
    def get_top_procedimientos(self):
        """Top 10 procedimientos más realizados"""
        return """
        SELECT 
            hp.CodiProc as Codigo,
            COALESCE(cp.NombProc, hp.CodiProc) as Nombre,
            COUNT(*) as Total
        FROM HojaProc hp
        LEFT JOIN CodiProc cp ON hp.CodiProc = cp.CodiProc
        WHERE hp.FechProc BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY hp.CodiProc, cp.NombProc
        ORDER BY Total DESC
        LIMIT 10
        """
    
    def get_procedimientos_por_hora(self):
        """Distribución de procedimientos por turno"""
        return """
        SELECT 
            CASE 
                WHEN HOUR(HoraProc) >= 6 AND HOUR(HoraProc) < 14 THEN 'Mañana (6am-2pm)'
                WHEN HOUR(HoraProc) >= 14 AND HOUR(HoraProc) < 22 THEN 'Tarde (2pm-10pm)'
                ELSE 'Noche (10pm-6am)'
            END as Turno,
            COUNT(*) as Total
        FROM HojaProc
        WHERE FechProc BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY Turno
        ORDER BY 
            CASE Turno
                WHEN 'Mañana (6am-2pm)' THEN 1
                WHEN 'Tarde (2pm-10pm)' THEN 2
                WHEN 'Noche (10pm-6am)' THEN 3
            END
        """
    
    def get_tendencia_semanal_procedimientos(self):
        """Tendencia de procedimientos últimos 7 días"""
        return """
        SELECT 
            DATE(FechProc) as Fecha,
            COUNT(*) as Total_Procedimientos
        FROM HojaProc
        WHERE FechProc >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            AND FechProc <= CURDATE()
        GROUP BY DATE(FechProc)
        ORDER BY Fecha
        """

    # ========================================================================
    # NUEVAS QUERIES - CIRUGÍAS MEJORADAS
    # ========================================================================
    
    def get_duracion_por_anestesia(self):
        """Duración promedio por tipo de anestesia"""
        return """
        SELECT 
            CASE aq.TipoAnes
                WHEN 1 THEN 'General'
                WHEN 2 THEN 'Regional'
                WHEN 3 THEN 'Local'
                ELSE 'Sin Especificar'
            END as Tipo_Anestesia,
            COUNT(*) as Total_Cirugias,
            ROUND(AVG(TIMESTAMPDIFF(MINUTE, 
                CONCAT(aq.FechInic, ' ', aq.HoraInic),
                CONCAT(aq.FechFina, ' ', aq.HoraFina)
            )), 0) as Promedio_Minutos
        FROM ActoQuir aq
        WHERE aq.FechInic BETWEEN :fecha_inicio AND :fecha_fin
            AND TIMESTAMPDIFF(MINUTE, 
                CONCAT(aq.FechInic, ' ', aq.HoraInic),
                CONCAT(aq.FechFina, ' ', aq.HoraFina)
            ) > 0
        GROUP BY aq.TipoAnes
        ORDER BY Total_Cirugias DESC
        """
    
    def get_cirugias_por_hora(self):
        """Distribución de cirugías por hora del día"""
        return """
        SELECT 
            HOUR(HoraInic) as Hora,
            COUNT(*) as Total
        FROM ActoQuir
        WHERE FechInic BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY HOUR(HoraInic)
        ORDER BY Hora
        """
    
    def get_cirugias_por_dia_semana(self):
        """Cirugías por día de la semana"""
        return """
        SELECT 
            CASE DAYOFWEEK(FechInic)
                WHEN 1 THEN 'Domingo'
                WHEN 2 THEN 'Lunes'
                WHEN 3 THEN 'Martes'
                WHEN 4 THEN 'Miércoles'
                WHEN 5 THEN 'Jueves'
                WHEN 6 THEN 'Viernes'
                WHEN 7 THEN 'Sábado'
            END as Dia_Semana,
            COUNT(*) as Total
        FROM ActoQuir
        WHERE FechInic BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY DAYOFWEEK(FechInic)
        ORDER BY DAYOFWEEK(FechInic)
        """
    
    def get_top_procedimientos_quirurgicos(self):
        """Top 10 procedimientos quirúrgicos (diagnóstico post)"""
        return """
        SELECT 
            DiagPost as Codigo,
            COUNT(*) as Total
        FROM ActoQuir
        WHERE FechInic BETWEEN :fecha_inicio AND :fecha_fin
            AND DiagPost IS NOT NULL 
            AND DiagPost != ''
        GROUP BY DiagPost
        ORDER BY Total DESC
        LIMIT 10
        """

    # ========================================================================
    # NUEVAS QUERIES - OCUPACIÓN MEJORADAS
    # ========================================================================
    
    def get_historico_ocupacion(self):
        """Ocupación de camas últimos 7 días"""
        return """
        SELECT 
            Fecha,
            Total_Camas,
            Camas_Ocupadas,
            ROUND((Camas_Ocupadas / Total_Camas) * 100, 1) as Porcentaje_Ocupacion
        FROM (
            SELECT 
                fechas.Fecha,
                COUNT(DISTINCT c.CodiCama) as Total_Camas,
                COUNT(DISTINCT CASE WHEN a.ConsAdmi IS NOT NULL THEN c.CodiCama END) as Camas_Ocupadas
            FROM (
                SELECT CURDATE() - INTERVAL 6 DAY as Fecha
                UNION SELECT CURDATE() - INTERVAL 5 DAY
                UNION SELECT CURDATE() - INTERVAL 4 DAY
                UNION SELECT CURDATE() - INTERVAL 3 DAY
                UNION SELECT CURDATE() - INTERVAL 2 DAY
                UNION SELECT CURDATE() - INTERVAL 1 DAY
                UNION SELECT CURDATE()
            ) fechas
            CROSS JOIN CodiCama c
            LEFT JOIN Admision a ON c.ConsAdmi = a.ConsAdmi 
                AND a.FechIngr <= fechas.Fecha
                AND (a.FechEgre >= fechas.Fecha OR a.FechEgre IS NULL OR a.FechEgre = '0000-00-00')
                AND a.Cerrado = 2
            WHERE c.Activa = 1
            GROUP BY fechas.Fecha
        ) datos
        ORDER BY Fecha
        """
    
    def get_rotacion_camas(self):
        """Rotación de camas - promedio de días ocupadas"""
        return """
        SELECT 
            c.CodiCama,
            c.NombCama,
            COUNT(DISTINCT a.ConsAdmi) as Veces_Usada,
            ROUND(AVG(DATEDIFF(
                CASE WHEN a.FechEgre = '0000-00-00' OR a.FechEgre IS NULL 
                     THEN CURDATE() 
                     ELSE a.FechEgre 
                END, 
                a.FechIngr
            )), 1) as Promedio_Dias_Ocupada
        FROM CodiCama c
        LEFT JOIN Admision a ON c.ConsAdmi = a.ConsAdmi 
            AND a.FechIngr >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        WHERE c.Activa = 1
            AND a.ConsAdmi IS NOT NULL
        GROUP BY c.CodiCama, c.NombCama
        ORDER BY Veces_Usada DESC
        LIMIT 20
        """
    
    def get_distribucion_tipo_cama(self):
        """Distribución de camas por tipo"""
        return """
        SELECT 
            CASE TipoCama
                WHEN 0 THEN 'Tipo 0'
                WHEN 1 THEN 'Tipo 1'
                WHEN 2 THEN 'Tipo 2'
                ELSE 'Otro'
            END as Tipo,
            COUNT(*) as Total,
            COUNT(CASE WHEN ConsAdmi IS NOT NULL AND ConsAdmi != '' THEN 1 END) as Ocupadas
        FROM CodiCama
        WHERE Activa = 1
        GROUP BY TipoCama
        ORDER BY Total DESC
        """
    
    def get_alertas_ocupacion(self):
        """Top 10 servicios con mayor ocupación (alertas)"""
        return """
        SELECT 
            COALESCE(cs.NombServ, c.CodiServ, 'Sin Servicio') as Servicio,
            COUNT(*) as Total_Camas,
            COUNT(CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 1 END) as Ocupadas,
            ROUND((COUNT(CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 1 END) / COUNT(*)) * 100, 1) as Porcentaje_Ocupacion
        FROM CodiCama c
        LEFT JOIN CodiServ cs ON c.CodiServ = cs.CodiServ
        WHERE c.Activa = 1
            AND c.CodiServ IS NOT NULL
            AND c.CodiServ != ''
        GROUP BY c.CodiServ, cs.NombServ
        HAVING COUNT(*) > 0
        ORDER BY Porcentaje_Ocupacion DESC
        LIMIT 10
        """

    # ========================================================================
    # NUEVAS QUERIES - PROFESIONALES MEJORADOS
    # ========================================================================
    
    def get_distribucion_carga_profesionales(self):
        """Distribución de carga de trabajo por profesional"""
        return """
        SELECT 
            UsuaCons as Profesional,
            COUNT(*) as Total_Atenciones,
            ROUND((COUNT(*) / (SELECT COUNT(*) FROM RipsCons WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin)) * 100, 1) as Porcentaje_Carga
        FROM RipsCons
        WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND UsuaCons IS NOT NULL
            AND UsuaCons != ''
        GROUP BY UsuaCons
        ORDER BY Total_Atenciones DESC
        LIMIT 15
        """
    
    def get_productividad_profesionales(self):
        """Productividad - atenciones realizadas vs pendientes"""
        return """
        SELECT 
            UsuaCons as Profesional,
            COUNT(*) as Total_Atenciones,
            COUNT(CASE WHEN EstaReal = 1 THEN 1 END) as Realizadas,
            COUNT(CASE WHEN EstaReal = 0 THEN 1 END) as Pendientes,
            ROUND((COUNT(CASE WHEN EstaReal = 1 THEN 1 END) / COUNT(*)) * 100, 1) as Porcentaje_Cumplimiento
        FROM RipsCons
        WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND UsuaCons IS NOT NULL
            AND UsuaCons != ''
        GROUP BY UsuaCons
        HAVING COUNT(*) >= 5
        ORDER BY Realizadas DESC
        LIMIT 15
        """
    
    def get_atenciones_por_servicio(self):
        """Distribución de atenciones por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, rc.CodiServ, 'Sin Definir') as Servicio,
            COUNT(*) as Total_Atenciones
        FROM RipsCons rc
        LEFT JOIN CodiServ cs ON rc.CodiServ = cs.CodiServ
        WHERE rc.FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND rc.CodiServ IS NOT NULL
            AND rc.CodiServ != ''
        GROUP BY rc.CodiServ, cs.NombServ
        ORDER BY Total_Atenciones DESC
        LIMIT 10
        """

    # ========================================================================
    # NUEVAS QUERIES - HISTORIA CLÍNICA MEJORADA
    # ========================================================================
    
    def get_busqueda_avanzada_historia(self, num_usua=None, fecha_desde=None, fecha_hasta=None, servicio=None):
        """Búsqueda avanzada de historia clínica"""
        conditions = ["a.Cerrado = 2"]
        
        if num_usua:
            conditions.append(f"a.NumeUsua = '{num_usua}'")
        if fecha_desde:
            conditions.append(f"a.FechIngr >= '{fecha_desde}'")
        if fecha_hasta:
            conditions.append(f"a.FechIngr <= '{fecha_hasta}'")
        if servicio:
            conditions.append(f"a.CodiServ = '{servicio}'")
        
        where_clause = " AND ".join(conditions)
        
        return f"""
        SELECT 
            a.ConsAdmi,
            a.NumeUsua,
            a.FechIngr,
            a.TipoAten,
            COALESCE(cs.NombServ, a.CodiServ) as Servicio,
            a.DiagIngr
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE {where_clause}
        ORDER BY a.FechIngr DESC
        LIMIT 50
        """
    
    def get_signos_vitales_timeline(self, cons_admi):
        """Timeline de signos vitales para gráfico"""
        return f"""
        SELECT 
            DATE_FORMAT(CONCAT(FechSigno, ' ', HoraSigno), '%Y-%m-%d %H:%i') as Fecha_Hora,
            TASist as Presion_Sistolica,
            TADias as Presion_Diastolica,
            Temperat as Temperatura,
            Pulso as Pulso,
            RespiMin as Frecuencia_Respiratoria
        FROM SignVita
        WHERE ConsAdmi = '{cons_admi}'
        ORDER BY FechSigno, HoraSigno
        """
    
    def get_medicamentos_agrupados(self, cons_admi):
        """Medicamentos agrupados y contabilizados"""
        return f"""
        SELECT 
            hm.CodiMedi as Codigo,
            COALESCE(cs.NombSumi, hm.CodiMedi) as Medicamento,
            COUNT(*) as Veces_Administrado,
            SUM(CASE WHEN hm.EstaSumi = 1 THEN 1 ELSE 0 END) as Aplicados,
            SUM(CASE WHEN hm.EstaSumi = 0 THEN 1 ELSE 0 END) as Pendientes
        FROM HojaMedi hm
        LEFT JOIN CodiSumi cs ON hm.CodiMedi = cs.CodiSumi
        WHERE hm.ConsAdmi = '{cons_admi}'
        GROUP BY hm.CodiMedi, cs.NombSumi
        ORDER BY Veces_Administrado DESC
        """

    # ========================================================================
    # QUERIES BÁSICAS PARA COMPATIBILIDAD CON MÓDULOS
    # ========================================================================
    
    def get_estadisticas_admisiones(self):
        """Estadísticas de admisiones con parámetros de fecha"""
        return """
        SELECT 
            COUNT(*) as Total_Admisiones,
            COUNT(CASE WHEN Cerrado = 2 THEN 1 END) as Activas,
            COUNT(CASE WHEN TipoAten = 1 THEN 1 END) as Urgencias,
            COUNT(CASE WHEN TipoAten = 2 THEN 1 END) as Hospitalizacion
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        """
    
    def get_distribucion_tipo_atencion(self):
        """Distribución por tipo de atención"""
        return """
        SELECT 
            CASE 
                WHEN TipoAten = 1 THEN 'Urgencias'
                WHEN TipoAten = 2 THEN 'Hospitalización'
                WHEN TipoAten = 3 THEN 'Consulta Externa'
                ELSE 'Otro'
            END as Tipo_Atencion,
            COUNT(*) as Total
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        GROUP BY TipoAten
        ORDER BY Total DESC
        """
    
    def get_estadisticas_facturacion(self):
        """Estadísticas de facturación"""
        return """
        SELECT 
            COUNT(*) as Total_Facturas,
            SUM(ValoTota) as Valor_Total,
            AVG(ValoTota) as Promedio,
            MAX(ValoTota) as Maximo
        FROM EncaFact
        WHERE FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 0
            AND ValoTota > 0
        """
    
    def get_distribucion_rangos(self):
        """Distribución de facturación por rangos"""
        return """
        SELECT 
            CASE 
                WHEN ValoTota < 100000 THEN 'Menos de $100K'
                WHEN ValoTota < 500000 THEN '$100K - $500K'
                WHEN ValoTota < 1000000 THEN '$500K - $1M'
                WHEN ValoTota < 5000000 THEN '$1M - $5M'
                ELSE 'Más de $5M'
            END as Rango,
            COUNT(*) as Total
        FROM EncaFact
        WHERE FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 0
            AND ValoTota > 0
        GROUP BY Rango
        ORDER BY MIN(ValoTota)
        """
    
    def get_facturacion_por_servicio_top(self):
        """Top servicios por facturación"""
        return """
        SELECT 
            COALESCE(cs.NombServ, ef.CodiServ, 'Sin Definir') as Servicio,
            SUM(ef.ValoTota) as Valor_Total
        FROM EncaFact ef
        LEFT JOIN CodiServ cs ON ef.CodiServ = cs.CodiServ
        WHERE ef.FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND ef.Anulado = 0
            AND ef.CodiServ IS NOT NULL
        GROUP BY ef.CodiServ, cs.NombServ
        ORDER BY Valor_Total DESC
        """
    
    def get_estadisticas_procedimientos(self):
        """Estadísticas de procedimientos"""
        return """
        SELECT 
            COUNT(*) as Total_Procedimientos,
            COUNT(DISTINCT CodiServ) as Servicios_Activos,
            COUNT(DISTINCT ConsAdmi) as Pacientes_Atendidos,
            COUNT(*) / DATEDIFF(:fecha_fin, :fecha_inicio) as Promedio_Por_Dia
        FROM HojaProc
        WHERE FechProc BETWEEN :fecha_inicio AND :fecha_fin
        """
    
    def get_procedimientos_por_servicio(self):
        """Procedimientos por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, hp.CodiServ, 'Sin Definir') as Servicio,
            COUNT(*) as Total
        FROM HojaProc hp
        LEFT JOIN CodiServ cs ON hp.CodiServ = cs.CodiServ
        WHERE hp.FechProc BETWEEN :fecha_inicio AND :fecha_fin
            AND hp.CodiServ IS NOT NULL
        GROUP BY hp.CodiServ, cs.NombServ
        ORDER BY Total DESC
        """
    
    def get_estadisticas_cirugias(self):
        """Estadísticas de cirugías"""
        return """
        SELECT 
            COUNT(*) as Total_Cirugias,
            ROUND(AVG(TIMESTAMPDIFF(MINUTE, 
                CONCAT(FechInic, ' ', HoraInic),
                CONCAT(FechFina, ' ', HoraFina)
            )), 0) as Duracion_Promedio,
            COUNT(CASE WHEN TipoAnes = 1 THEN 1 END) as Anestesia_General,
            COUNT(CASE WHEN TipoAnes = 2 THEN 1 END) as Anestesia_Regional
        FROM ActoQuir
        WHERE FechInic BETWEEN :fecha_inicio AND :fecha_fin
        """
    
    def get_distribucion_anestesia(self):
        """Distribución por tipo de anestesia"""
        return """
        SELECT 
            CASE TipoAnes
                WHEN 1 THEN 'General'
                WHEN 2 THEN 'Regional'
                WHEN 3 THEN 'Local'
                ELSE 'Sin Especificar'
            END as Tipo_Anestesia,
            COUNT(*) as Total
        FROM ActoQuir
        WHERE FechInic BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY TipoAnes
        ORDER BY Total DESC
        """
    
    def get_ocupacion_general(self):
        """Ocupación general de camas"""
        return """
        SELECT 
            COUNT(*) as Total_Camas,
            COUNT(CASE WHEN ConsAdmi IS NOT NULL AND ConsAdmi != '' THEN 1 END) as Ocupadas,
            COUNT(CASE WHEN ConsAdmi IS NULL OR ConsAdmi = '' THEN 1 END) as Libres,
            ROUND((COUNT(CASE WHEN ConsAdmi IS NOT NULL AND ConsAdmi != '' THEN 1 END) / COUNT(*)) * 100, 1) as Porcentaje_Ocupacion
        FROM CodiCama
        WHERE Activa = 1
        """
    
    def get_ocupacion_por_servicio(self):
        """Ocupación por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, c.CodiServ, 'Sin Servicio') as Servicio,
            COUNT(*) as Total_Camas,
            COUNT(CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 1 END) as Ocupadas,
            ROUND((COUNT(CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN 1 END) / COUNT(*)) * 100, 1) as Porcentaje_Ocupacion
        FROM CodiCama c
        LEFT JOIN CodiServ cs ON c.CodiServ = cs.CodiServ
        WHERE c.Activa = 1
            AND c.CodiServ IS NOT NULL
            AND c.CodiServ != ''
        GROUP BY c.CodiServ, cs.NombServ
        ORDER BY Porcentaje_Ocupacion DESC
        """
    
    def get_estadisticas_profesionales(self):
        """Estadísticas de profesionales"""
        return """
        SELECT 
            COUNT(*) as Total_Atenciones,
            COUNT(DISTINCT UsuaCons) as Profesionales_Activos,
            COUNT(CASE WHEN EstaReal = 1 THEN 1 END) as Atenciones_Realizadas,
            COUNT(CASE WHEN EstaReal = 0 THEN 1 END) as Atenciones_Pendientes
        FROM RipsCons
        WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND UsuaCons IS NOT NULL
            AND UsuaCons != ''
        """
    
    def get_top_profesionales(self):
        """Top profesionales por atenciones"""
        return """
        SELECT 
            UsuaCons as Profesional,
            COUNT(*) as Total_Atenciones
        FROM RipsCons
        WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND UsuaCons IS NOT NULL
            AND UsuaCons != ''
        GROUP BY UsuaCons
        ORDER BY Total_Atenciones DESC
        LIMIT 20
        """

    # ========================================================================
    # NUEVAS SECCIONES - 7 ANÁLISIS AVANZADOS
    # ========================================================================
    
    def get_readmisiones_30_dias(self):
        """Pacientes readmitidos en los últimos 30 días"""
        return """
        SELECT 
            p.NumeUsua,
            CONCAT(p.NombUsua, ' ', p.ApelUsua) as Nombre_Paciente,
            COUNT(*) as Total_Readmisiones,
            MIN(a.FechIngr) as Primera_Admision,
            MAX(a.FechIngr) as Ultima_Admision,
            DATEDIFF(MAX(a.FechIngr), MIN(a.FechIngr)) as Dias_Entre_Admisiones
        FROM Admision a
        INNER JOIN Paciente p ON a.NumeUsua = p.NumeUsua
        WHERE a.FechIngr >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND a.Anulado = 2
        GROUP BY p.NumeUsua, p.NombUsua, p.ApelUsua
        HAVING Total_Readmisiones > 1
        ORDER BY Total_Readmisiones DESC, Dias_Entre_Admisiones ASC
        LIMIT 100
        """
    
    def get_tasa_readmision_por_servicio(self):
        """Tasa de readmisión por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, a.CodiServ, 'Sin Definir') as Servicio,
            COUNT(DISTINCT a.NumeUsua) as Total_Pacientes,
            COUNT(DISTINCT CASE 
                WHEN EXISTS (
                    SELECT 1 FROM Admision a2 
                    WHERE a2.NumeUsua = a.NumeUsua 
                        AND a2.FechIngr > a.FechIngr
                        AND a2.FechIngr <= DATE_ADD(a.FechIngr, INTERVAL 30 DAY)
                        AND a2.Anulado = 2
                ) THEN a.NumeUsua 
            END) as Pacientes_Readmitidos,
            ROUND(
                (COUNT(DISTINCT CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM Admision a2 
                        WHERE a2.NumeUsua = a.NumeUsua 
                            AND a2.FechIngr > a.FechIngr
                            AND a2.FechIngr <= DATE_ADD(a.FechIngr, INTERVAL 30 DAY)
                            AND a2.Anulado = 2
                    ) THEN a.NumeUsua 
                END) / NULLIF(COUNT(DISTINCT a.NumeUsua), 0)) * 100,
                1
            ) as Tasa_Readmision
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE a.FechIngr >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
            AND a.Anulado = 2
        GROUP BY a.CodiServ, cs.NombServ
        HAVING Total_Pacientes > 5
        ORDER BY Tasa_Readmision DESC
        """
    
    def get_flujo_pacientes(self):
        """Flujo de pacientes entre servicios (traslados)"""
        return """
        SELECT 
            COALESCE(cs1.NombServ, t.ServOrig, 'Origen Desconocido') as Servicio_Origen,
            COALESCE(cs2.NombServ, t.ServDest, 'Destino Desconocido') as Servicio_Destino,
            COUNT(*) as Total_Traslados
        FROM TrasCama t
        LEFT JOIN CodiServ cs1 ON t.ServOrig = cs1.CodiServ
        LEFT JOIN CodiServ cs2 ON t.ServDest = cs2.CodiServ
        WHERE t.FechTras >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY t.ServOrig, t.ServDest, cs1.NombServ, cs2.NombServ
        HAVING Total_Traslados > 1
        ORDER BY Total_Traslados DESC
        LIMIT 50
        """
    
    def get_tiempos_espera_procedimientos(self):
        """Tiempos de espera promedio entre orden y realización"""
        return """
        SELECT 
            COALESCE(cs.NombServ, a.CodiServ, 'Sin Definir') as Servicio,
            COUNT(*) as Total_Procedimientos,
            ROUND(AVG(DATEDIFF(hp.FechProc, eo.FechOrde)), 1) as Dias_Espera_Promedio,
            MIN(DATEDIFF(hp.FechProc, eo.FechOrde)) as Dias_Espera_Minimo,
            MAX(DATEDIFF(hp.FechProc, eo.FechOrde)) as Dias_Espera_Maximo
        FROM HojaProc hp
        INNER JOIN EncaOrde eo ON hp.ConsAdmi = eo.ConsAdmi AND hp.ConsOrde = eo.ConsOrde
        INNER JOIN Admision a ON hp.ConsAdmi = a.ConsAdmi
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE hp.FechProc >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND eo.FechOrde < hp.FechProc
        GROUP BY a.CodiServ, cs.NombServ
        HAVING Total_Procedimientos > 3
        ORDER BY Dias_Espera_Promedio DESC
        LIMIT 20
        """
    
    def get_distribucion_tiempos_espera(self):
        """Distribución de procedimientos por rango de tiempo de espera"""
        return """
        SELECT 
            CASE 
                WHEN DATEDIFF(hp.FechProc, eo.FechOrde) = 0 THEN 'Mismo día'
                WHEN DATEDIFF(hp.FechProc, eo.FechOrde) BETWEEN 1 AND 3 THEN '1-3 días'
                WHEN DATEDIFF(hp.FechProc, eo.FechOrde) BETWEEN 4 AND 7 THEN '4-7 días'
                WHEN DATEDIFF(hp.FechProc, eo.FechOrde) BETWEEN 8 AND 15 THEN '8-15 días'
                ELSE 'Más de 15 días'
            END as Rango_Espera,
            COUNT(*) as Total_Procedimientos
        FROM HojaProc hp
        INNER JOIN EncaOrde eo ON hp.ConsAdmi = eo.ConsAdmi AND hp.ConsOrde = eo.ConsOrde
        WHERE hp.FechProc >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND eo.FechOrde < hp.FechProc
        GROUP BY Rango_Espera
        ORDER BY 
            CASE Rango_Espera
                WHEN 'Mismo día' THEN 1
                WHEN '1-3 días' THEN 2
                WHEN '4-7 días' THEN 3
                WHEN '8-15 días' THEN 4
                ELSE 5
            END
        """
    
    def get_uso_quirofanos(self):
        """Uso y estadísticas de quirófanos"""
        return """
        SELECT 
            aq.Quirofan as Quirofano,
            COUNT(*) as Total_Cirugias,
            ROUND(AVG(TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina)), 0) as Duracion_Promedio_Minutos,
            SUM(TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina)) / 60.0 as Horas_Totales_Uso,
            ROUND(
                (SUM(TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina)) / 60.0) / 
                (DATEDIFF(CURDATE(), DATE_SUB(CURDATE(), INTERVAL 30 DAY)) * 12) * 100,
                1
            ) as Porcentaje_Utilizacion
        FROM ActoQuir aq
        WHERE aq.FechInic >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND aq.Quirofan IS NOT NULL
            AND aq.HoraInic IS NOT NULL
            AND aq.HoraFina IS NOT NULL
            AND aq.HoraFina > aq.HoraInic
        GROUP BY aq.Quirofan
        HAVING Total_Cirugias > 0
        ORDER BY Total_Cirugias DESC
        """
    
    def get_analisis_duracion_cirugias(self):
        """Análisis de duración de cirugías por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, a.CodiServ, 'Sin Definir') as Servicio,
            COUNT(*) as Total_Cirugias,
            ROUND(AVG(TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina)), 0) as Duracion_Promedio,
            MIN(TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina)) as Duracion_Minima,
            MAX(TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina)) as Duracion_Maxima,
            ROUND(STDDEV(TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina)), 0) as Desviacion_Estandar
        FROM ActoQuir aq
        INNER JOIN Admision a ON aq.ConsAdmi = a.ConsAdmi
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE aq.FechInic BETWEEN :fecha_inicio AND :fecha_fin
            AND aq.HoraInic IS NOT NULL
            AND aq.HoraFina IS NOT NULL
            AND aq.HoraFina > aq.HoraInic
        GROUP BY a.CodiServ, cs.NombServ
        HAVING Total_Cirugias > 2
        ORDER BY Total_Cirugias DESC
        LIMIT 15
        """
    
    def get_distribucion_duracion(self):
        """Distribución de cirugías por rango de duración"""
        return """
        SELECT 
            CASE 
                WHEN TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina) < 30 THEN 'Menos de 30 min'
                WHEN TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina) BETWEEN 30 AND 60 THEN '30-60 min'
                WHEN TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina) BETWEEN 61 AND 120 THEN '1-2 horas'
                WHEN TIMESTAMPDIFF(MINUTE, aq.HoraInic, aq.HoraFina) BETWEEN 121 AND 180 THEN '2-3 horas'
                ELSE 'Más de 3 horas'
            END as Rango_Duracion,
            COUNT(*) as Total_Cirugias
        FROM ActoQuir aq
        WHERE aq.FechInic BETWEEN :fecha_inicio AND :fecha_fin
            AND aq.HoraInic IS NOT NULL
            AND aq.HoraFina IS NOT NULL
            AND aq.HoraFina > aq.HoraInic
        GROUP BY Rango_Duracion
        ORDER BY 
            CASE Rango_Duracion
                WHEN 'Menos de 30 min' THEN 1
                WHEN '30-60 min' THEN 2
                WHEN '1-2 horas' THEN 3
                WHEN '2-3 horas' THEN 4
                ELSE 5
            END
        """
    
    def get_rotacion_personal(self):
        """Distribución de consultas por turno por profesional"""
        return """
        SELECT 
            CONCAT(u.NombUsua, ' ', u.ApelUsua) as Profesional,
            COALESCE(ce.NombEspe, 'Sin Especialidad') as Especialidad,
            COUNT(*) as Total_Consultas,
            COUNT(CASE WHEN HOUR(rc.HoraCons) BETWEEN 6 AND 13 THEN 1 END) as Turno_Manana,
            COUNT(CASE WHEN HOUR(rc.HoraCons) BETWEEN 14 AND 20 THEN 1 END) as Turno_Tarde,
            COUNT(CASE WHEN HOUR(rc.HoraCons) BETWEEN 21 AND 23 OR HOUR(rc.HoraCons) BETWEEN 0 AND 5 THEN 1 END) as Turno_Noche
        FROM RipsCons rc
        INNER JOIN Usuarios u ON rc.CodiMedi = u.CodiUsua
        LEFT JOIN CodiEspe ce ON u.CodiEspe = ce.CodiEspe
        WHERE rc.FechCons >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND rc.HoraCons IS NOT NULL
        GROUP BY u.CodiUsua, u.NombUsua, u.ApelUsua, ce.NombEspe
        HAVING Total_Consultas > 5
        ORDER BY Total_Consultas DESC
        LIMIT 100
        """
    
    def get_distribucion_turnos(self):
        """Distribución general de consultas por turno"""
        return """
        SELECT 
            CASE 
                WHEN HOUR(rc.HoraCons) BETWEEN 6 AND 13 THEN 'Mañana (6am-1pm)'
                WHEN HOUR(rc.HoraCons) BETWEEN 14 AND 20 THEN 'Tarde (2pm-8pm)'
                ELSE 'Noche (9pm-5am)'
            END as Turno,
            COUNT(*) as Total_Consultas
        FROM RipsCons rc
        WHERE rc.FechCons >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND rc.HoraCons IS NOT NULL
        GROUP BY Turno
        ORDER BY 
            CASE Turno
                WHEN 'Mañana (6am-1pm)' THEN 1
                WHEN 'Tarde (2pm-8pm)' THEN 2
                ELSE 3
            END
        """
    
    def get_eficiencia_camas(self):
        """Indicadores de eficiencia de camas por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, c.CodiServ, 'Sin Servicio') as Servicio,
            COUNT(DISTINCT c.CodiCama) as Total_Camas,
            COUNT(DISTINCT CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN c.CodiCama END) as Camas_Ocupadas,
            ROUND(
                (COUNT(DISTINCT CASE WHEN c.ConsAdmi IS NOT NULL AND c.ConsAdmi != '' THEN c.CodiCama END) / 
                 NULLIF(COUNT(DISTINCT c.CodiCama), 0)) * 100,
                1
            ) as Porcentaje_Ocupacion,
            ROUND(
                COUNT(DISTINCT a.ConsAdmi) / NULLIF(COUNT(DISTINCT c.CodiCama), 0),
                2
            ) as Indice_Rotacion,
            ROUND(
                AVG(DATEDIFF(COALESCE(a.FechEgre, CURDATE()), a.FechIngr)),
                1
            ) as Estancia_Promedio_Dias
        FROM CodiCama c
        LEFT JOIN CodiServ cs ON c.CodiServ = cs.CodiServ
        LEFT JOIN Admision a ON c.CodiServ = a.CodiServ 
            AND a.FechIngr >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND a.Anulado = 2
        WHERE c.Activa = 1
            AND c.CodiServ IS NOT NULL
            AND c.CodiServ != ''
        GROUP BY c.CodiServ, cs.NombServ
        HAVING Total_Camas > 0
        ORDER BY Indice_Rotacion DESC
        """

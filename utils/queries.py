"""
SIHOS Queries - VERSIÓN COMPLETA ACTUALIZADA
Todas las queries corregidas con campos reales de la BD
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
            COUNT(CASE WHEN TipoAten = 3 THEN 1 END) as Urgencias,
            COUNT(CASE WHEN TipoAten = 2 THEN 1 END) as Hospitalizacion,
            COUNT(CASE WHEN TipoAten = 1 THEN 1 END) as Consulta_Externa,
            COUNT(CASE WHEN TipoAten = 4 THEN 1 END) as PyP
        FROM Admision
        WHERE DATE(FechIngr) = CURDATE()
            AND Anulado = 2
        """
    
    def get_estadisticas_admisiones(self):
        """Estadísticas de admisiones con parámetros de fecha"""
        return """
        SELECT
            COUNT(*) as Total_Admisiones,
            COUNT(CASE WHEN Cerrado = 2 THEN 1 END) as Activas,
            COUNT(CASE WHEN TipoAten = 3 THEN 1 END) as Urgencias,
            COUNT(CASE WHEN TipoAten = 2 THEN 1 END) as Hospitalizacion,
            COUNT(CASE WHEN TipoAten = 1 THEN 1 END) as Consulta_Externa,
            COUNT(CASE WHEN TipoAten = 4 THEN 1 END) as PyP
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        """
    
    def get_distribucion_tipo_atencion(self):
        """Distribución por tipo de atención"""
        return """
        SELECT
            CASE
                WHEN TipoAten = 1 THEN 'Consulta Externa'
                WHEN TipoAten = 2 THEN 'Hospitalización'
                WHEN TipoAten = 3 THEN 'Urgencias'
                WHEN TipoAten = 4 THEN 'Promoción y Prevención'
                ELSE 'Otro'
            END as Tipo_Atencion,
            COUNT(*) as Total
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        GROUP BY TipoAten
        ORDER BY Total DESC
        """
    
    def get_admisiones_por_servicio(self):
        """Por servicio con promedio de estancia"""
        return """
        SELECT 
            COALESCE(cs.NombServ, a.CodiServ) as Servicio,
            COUNT(*) as Total_Admisiones,
            COUNT(CASE WHEN a.Cerrado = 2 THEN 1 END) as Activas,
            COUNT(CASE WHEN a.Cerrado = 1 THEN 1 END) as Cerradas,
            COUNT(CASE WHEN a.TipoAten = 3 THEN 1 END) as Urgencias,
            COUNT(CASE WHEN a.TipoAten = 2 THEN 1 END) as Hospitalizacion,
            ROUND(AVG(DATEDIFF(COALESCE(a.FechEgre, CURDATE()), a.FechIngr)), 1) as Promedio_Estancia
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND a.Anulado = 2
        GROUP BY cs.NombServ, a.CodiServ
        ORDER BY Total_Admisiones DESC
        """
    
    def get_distribucion_estado(self):
        """Distribución por estado de admisión"""
        return """
        SELECT 
            CASE 
                WHEN Cerrado = 1 THEN 'Cerrada'
                WHEN Cerrado = 2 THEN 'Activa'
                ELSE 'Otro'
            END as Estado,
            COUNT(*) as Total
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        GROUP BY Cerrado
        ORDER BY Total DESC
        """
    
    def get_distribucion_regimen_corregido(self):
        """Distribución por régimen de afiliación"""
        return """
        SELECT 
            CASE 
                WHEN TipoAfil = 'A' THEN 'Tipo A'
                WHEN TipoAfil = 'B' THEN 'Tipo B'
                WHEN TipoAfil = 'C' THEN 'Tipo C'
                WHEN TipoAfil = 'D' THEN 'Tipo D'
                ELSE 'No Especificado'
            END as Regimen,
            COUNT(*) as Total
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        GROUP BY TipoAfil
        ORDER BY Total DESC
        """
    
    def get_distribucion_edad_corregido(self):
        """Distribución por rango de edad"""
        return """
        SELECT 
            CASE 
                WHEN a.ValoEdad < 18 AND a.UnidEdad = 'A' THEN 'Menores de 18'
                WHEN a.ValoEdad BETWEEN 18 AND 40 AND a.UnidEdad = 'A' THEN '18-40 años'
                WHEN a.ValoEdad BETWEEN 41 AND 60 AND a.UnidEdad = 'A' THEN '41-60 años'
                WHEN a.ValoEdad > 60 AND a.UnidEdad = 'A' THEN 'Mayores de 60'
                WHEN a.UnidEdad IN ('M', 'D') THEN 'Menores de 18'
                ELSE 'Sin Especificar'
            END as Rango_Edad,
            COUNT(*) as Total
        FROM Admision a
        WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND a.Anulado = 2
        GROUP BY Rango_Edad
        ORDER BY 
            CASE Rango_Edad
                WHEN 'Menores de 18' THEN 1
                WHEN '18-40 años' THEN 2
                WHEN '41-60 años' THEN 3
                WHEN 'Mayores de 60' THEN 4
                ELSE 5
            END
        """
    
    def get_distribucion_genero_corregido(self):
        """Distribución por género"""
        return """
        SELECT 
            CASE 
                WHEN p.SexoUsua = 'M' THEN 'Masculino'
                WHEN p.SexoUsua = 'F' THEN 'Femenino'
                ELSE 'No Especificado'
            END as Genero,
            COUNT(*) as Total
        FROM Admision a
        INNER JOIN Paciente p ON a.NumeUsua = p.NumeUsua
        WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND a.Anulado = 2
        GROUP BY p.SexoUsua
        ORDER BY Total DESC
        """
    
    def get_distribucion_tipo_documento(self):
        """Distribución por tipo de documento"""
        return """
        SELECT 
            CASE 
                WHEN TipoDocu = 'CC' THEN 'Cédula de Ciudadanía'
                WHEN TipoDocu = 'TI' THEN 'Tarjeta de Identidad'
                WHEN TipoDocu = 'RC' THEN 'Registro Civil'
                WHEN TipoDocu = 'CN' THEN 'Certificado Nacido Vivo'
                WHEN TipoDocu = 'CE' THEN 'Cédula de Extranjería'
                WHEN TipoDocu = 'PA' THEN 'Pasaporte'
                ELSE CONCAT('Otro (', TipoDocu, ')')
            END as Tipo_Documento,
            COUNT(*) as Total
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        GROUP BY TipoDocu
        ORDER BY Total DESC
        """
    
    def get_distribucion_estrato(self):
        """Distribución por estrato socioeconómico"""
        return """
        SELECT 
            CASE 
                WHEN CodiEstr = '0' THEN 'Estrato 0'
                WHEN CodiEstr = '1' THEN 'Estrato 1'
                WHEN CodiEstr = '2' THEN 'Estrato 2'
                WHEN CodiEstr = '3' THEN 'Estrato 3'
                WHEN CodiEstr = '4' THEN 'Estrato 4'
                WHEN CodiEstr = '5' THEN 'Estrato 5'
                WHEN CodiEstr = '6' THEN 'Estrato 6'
                ELSE 'No Especificado'
            END as Estrato,
            COUNT(*) as Total
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        GROUP BY CodiEstr
        ORDER BY 
            CASE 
                WHEN CodiEstr IN ('0','1','2','3','4','5','6') THEN CAST(CodiEstr AS UNSIGNED)
                ELSE 100
            END
        """
    
    def get_distribucion_via_ingreso(self):
        """Distribución por vía de ingreso"""
        return """
        SELECT 
            CASE 
                WHEN ViaIngre = 1 THEN 'Referencia de Otra Institución'
                WHEN ViaIngre = 2 THEN 'Espontáneo / Demanda'
                WHEN ViaIngre = 3 THEN 'Remisión'
                WHEN ViaIngre = 4 THEN 'Contraremisión'
                WHEN ViaIngre = 11 THEN 'Otro'
                ELSE CONCAT('Tipo ', ViaIngre)
            END as Via_Ingreso,
            COUNT(*) as Total
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
            AND ViaIngre IS NOT NULL
        GROUP BY ViaIngre
        ORDER BY Total DESC
        """
    
    def get_tendencias_admisiones_completas(self):
        """Tendencias con múltiples métricas"""
        return """
        SELECT 
            DATE(FechIngr) as Fecha,
            COUNT(*) as Total_Admisiones,
            COUNT(CASE WHEN TipoAten = 3 THEN 1 END) as Urgencias,
            COUNT(CASE WHEN TipoAten = 2 THEN 1 END) as Hospitalizacion,
            COUNT(CASE WHEN TipoAten = 1 THEN 1 END) as Consulta_Externa,
            ROUND(COUNT(*) / 1.0, 1) as Promedio_Diario,
            ROUND((COUNT(CASE WHEN TipoAten = 2 AND Cerrado = 2 AND Anulado = 2 THEN 1 END) /
                (SELECT COUNT(*) FROM CodiCama WHERE Activa = 1 AND Habilita = 1)) * 100, 1) as Porcentaje_Ocupacion
        FROM Admision
        WHERE FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        GROUP BY DATE(FechIngr)
        ORDER BY Fecha
        """
    
    def get_top_diagnosticos_ingreso_completo(self):
        """Top diagnósticos de ingreso SIN LÍMITE"""
        return """
        SELECT 
            DiagIngr as Codigo,
            COUNT(*) as Total
        FROM Admision
        WHERE DiagIngr IS NOT NULL 
            AND DiagIngr != ''
            AND FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 2
        GROUP BY DiagIngr
        ORDER BY Total DESC
        """
    
    def get_tiempos_estancia(self):
        """Distribución de tiempos de estancia para hospitalización"""
        return """
        SELECT 
            CASE 
                WHEN DATEDIFF(FechEgre, FechIngr) <= 1 THEN '1 día o menos'
                WHEN DATEDIFF(FechEgre, FechIngr) = 2 THEN '2 días'
                WHEN DATEDIFF(FechEgre, FechIngr) >= 3 THEN '3 días o más'
            END as Rango,
            COUNT(*) as Total
        FROM Admision
        WHERE TipoAten = 2
            AND FechEgre IS NOT NULL 
            AND FechEgre != '0000-00-00'
            AND FechIngr >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND Anulado = 2
        GROUP BY Rango
        ORDER BY 
            CASE Rango
                WHEN '1 día o menos' THEN 1
                WHEN '2 días' THEN 2
                WHEN '3 días o más' THEN 3
            END
        """
    
    def get_readmisiones_30_dias(self):
        """Pacientes readmitidos en 30 días"""
        return """
        SELECT 
            a1.NumeUsua,
            COALESCE(p.NombUsua, a1.NumeUsua) as Paciente,
            -- Contamos cuántos ingresos únicos de 'a2' califican como reingreso
            COUNT(DISTINCT a2.ConsAdmi) as Total_Readmisiones, 
            MIN(a1.FechIngr) as Primera_Admision,
            MAX(a2.FechIngr) as Ultima_Readmision,
            -- Listamos los servicios a los que reingresó
            GROUP_CONCAT(DISTINCT COALESCE(cs.NombServ, a2.CodiServ) SEPARATOR ', ') as Servicios_Reingreso
        FROM Admision a1
        INNER JOIN Admision a2 ON a1.NumeUsua = a2.NumeUsua 
            AND a2.FechIngr > a1.FechIngr 
            AND DATEDIFF(a2.FechIngr, a1.FechIngr) <= 30
            AND a2.Anulado = 2  -- Aseguramos que el reingreso también sea válido
        LEFT JOIN Paciente p ON a1.NumeUsua = p.NumeUsua
        LEFT JOIN CodiServ cs ON a2.CodiServ = cs.CodiServ -- Traemos el servicio del reingreso
        WHERE a1.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND a1.Anulado = 2
        GROUP BY a1.NumeUsua, p.NombUsua
        ORDER BY Total_Readmisiones DESC
        LIMIT 100
        """

    def get_tasa_readmision_por_servicio(self):
        """Tasa de readmisión por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, a.CodiServ, 'Sin Definir') as Servicio,
            COUNT(DISTINCT a.ConsAdmi) as Total_Admisiones,
            COUNT(DISTINCT CASE 
                WHEN EXISTS (
                    SELECT 1 FROM Admision a2 
                    WHERE a2.NumeUsua = a.NumeUsua 
                    AND a2.FechIngr > a.FechIngr 
                    AND DATEDIFF(a2.FechIngr, a.FechIngr) <= 30
                ) THEN a.ConsAdmi 
            END) as Readmisiones,
            ROUND(
                (COUNT(DISTINCT CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM Admision a2 
                        WHERE a2.NumeUsua = a.NumeUsua 
                        AND a2.FechIngr > a.FechIngr 
                        AND DATEDIFF(a2.FechIngr, a.FechIngr) <= 30
                    ) THEN a.ConsAdmi 
                END) / NULLIF(COUNT(DISTINCT a.ConsAdmi), 0)) * 100,
                2
            ) as Tasa_Readmision
        FROM Admision a
        LEFT JOIN CodiServ cs ON a.CodiServ = cs.CodiServ
        WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
            AND a.Anulado = 2
        GROUP BY a.CodiServ, cs.NombServ
        HAVING Total_Admisiones > 5
        ORDER BY Tasa_Readmision DESC
        """
    
    # ========================================================================
    # FACTURACIÓN
    # ========================================================================
    
    def get_facturacion_hoy(self):
        """Facturación del día actual — fuente: DetaFact (valor real por ítems)"""
        return """
        SELECT
            COALESCE(SUM(df.ValoTota), 0) AS Valor_Total,
            COUNT(DISTINCT CONCAT(ef.CodiInst, ef.CodiAno, ef.CodiDocu, ef.NumeFact)) AS Total_Facturas,
            ROUND(
                COALESCE(SUM(df.ValoTota), 0)
                / NULLIF(COUNT(DISTINCT CONCAT(ef.CodiInst, ef.CodiAno, ef.CodiDocu, ef.NumeFact)), 0)
            , 0) AS Promedio_Factura,
            MAX(df.ValoTota) AS Factura_Mayor
        FROM DetaFact df
        JOIN EncaFact ef
            ON  ef.CodiInst = df.CodiInst
            AND ef.CodiAno  = df.CodiAno
            AND ef.CodiDocu = df.CodiDocu
            AND ef.NumeFact = df.NumeFact
        WHERE ef.Anulado = 0
          AND DATE(ef.FechFact) = CURDATE()
        """
    
    def get_estadisticas_facturacion(self):
        """Estadísticas de facturación — fuente: DetaFact (valor real por ítems)"""
        return """
        SELECT
            COALESCE(SUM(df.ValoTota), 0) AS Valor_Total,
            COUNT(DISTINCT CONCAT(ef.CodiInst, ef.CodiAno, ef.CodiDocu, ef.NumeFact)) AS Total_Facturas,
            ROUND(
                COALESCE(SUM(df.ValoTota), 0)
                / NULLIF(COUNT(DISTINCT CONCAT(ef.CodiInst, ef.CodiAno, ef.CodiDocu, ef.NumeFact)), 0)
            , 0) AS Valor_Promedio,
            MAX(df.ValoTota) AS Valor_Maximo
        FROM DetaFact df
        JOIN EncaFact ef
            ON  ef.CodiInst = df.CodiInst
            AND ef.CodiAno  = df.CodiAno
            AND ef.CodiDocu = df.CodiDocu
            AND ef.NumeFact = df.NumeFact
        WHERE ef.Anulado = 0
          AND ef.FechFact BETWEEN :fecha_inicio AND :fecha_fin
        """
    
    def get_facturacion_por_rango(self):
        """Distribución por rangos de valor"""
        return """
        SELECT 
            CASE 
                WHEN ValoTota < 100000 THEN 'Menos de $100K'
                WHEN ValoTota < 500000 THEN '$100K - $500K'
                WHEN ValoTota < 1000000 THEN '$500K - $1M'
                WHEN ValoTota < 5000000 THEN '$1M - $5M'
                WHEN ValoTota < 10000000 THEN '$5M - $10M'
                ELSE 'Más de $10M'
            END as Rango,
            COUNT(*) as Total
        FROM EncaFact
        WHERE FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 0
            AND ValoTota > 0
        GROUP BY Rango
        ORDER BY MIN(ValoTota)
        """
    
    def get_facturacion_por_tipo_afiliacion(self):
        """Facturación por tipo de afiliación"""
        return """
        SELECT 
            CASE 
                WHEN TipoAfil = 'A' THEN 'Tipo A'
                WHEN TipoAfil = 'B' THEN 'Tipo B'
                WHEN TipoAfil = 'C' THEN 'Tipo C'
                WHEN TipoAfil = 'D' THEN 'Tipo D'
                ELSE 'No Especificado'
            END as Tipo,
            COUNT(*) as Total_Facturas,
            SUM(ValoTota) as Valor_Total
        FROM EncaFact
        WHERE FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 0
        GROUP BY TipoAfil
        ORDER BY Valor_Total DESC
        """
    
    def get_facturacion_por_servicio(self):
        """Facturación por servicio"""
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
    
    def get_facturacion_por_tipo_documento(self):
        """Facturación por tipo de documento"""
        return """
        SELECT
            CASE
                WHEN TipoDocu = 'CC' THEN 'Cédula de Ciudadanía'
                WHEN TipoDocu = 'TI' THEN 'Tarjeta de Identidad'
                WHEN TipoDocu = 'RC' THEN 'Registro Civil'
                WHEN TipoDocu = 'CN' THEN 'Certificado Nacido Vivo'
                WHEN TipoDocu = 'CE' THEN 'Cédula de Extranjería'
                WHEN TipoDocu = 'PA' THEN 'Pasaporte'
                ELSE CONCAT('Otro (', COALESCE(TipoDocu, 'ND'), ')')
            END as Tipo_Documento,
            COUNT(*) as Total_Facturas,
            SUM(ValoTota) as Valor_Total
        FROM EncaFact
        WHERE FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 0
        GROUP BY TipoDocu
        ORDER BY Valor_Total DESC
        """
    
    def get_facturacion_por_estado(self):
        """Facturación por estado (anulado/activo)"""
        return """
        SELECT 
            CASE 
                WHEN Anulado = 0 THEN 'Activa'
                WHEN Anulado = 1 THEN 'Anulada'
                ELSE 'Otro'
            END as Estado,
            COUNT(*) as Total_Facturas,
            SUM(ValoTota) as Valor_Total
        FROM EncaFact
        WHERE FechFact BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY Anulado
        ORDER BY Valor_Total DESC
        """
    
    def get_facturacion_por_mes(self):
        """Facturación agrupada por mes"""
        return """
        SELECT 
            DATE_FORMAT(FechFact, '%Y-%m') as Mes,
            DATE_FORMAT(FechFact, '%M %Y') as Mes_Nombre,
            COUNT(*) as Total_Facturas,
            SUM(ValoTota) as Valor_Total
        FROM EncaFact
        WHERE FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 0
        GROUP BY DATE_FORMAT(FechFact, '%Y-%m')
        ORDER BY Mes
        """
    
    def get_top_facturas_altas(self):
        """Top facturas más altas"""
        return """
        SELECT 
            NumeFact as Numero_Factura,
            FechFact as Fecha,
            COALESCE(cs.NombServ, ef.CodiServ) as Servicio,
            CASE 
                WHEN TipoAfil = 'A' THEN 'Tipo A'
                WHEN TipoAfil = 'B' THEN 'Tipo B'
                WHEN TipoAfil = 'C' THEN 'Tipo C'
                WHEN TipoAfil = 'D' THEN 'Tipo D'
                ELSE 'No Especificado'
            END as Tipo_Afiliacion,
            ValoTota as Valor_Total
        FROM EncaFact ef
        LEFT JOIN CodiServ cs ON ef.CodiServ = cs.CodiServ
        WHERE FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND Anulado = 0
            AND ValoTota > 0
        ORDER BY ValoTota DESC
        LIMIT 100
        """
    
    def get_analisis_cartera(self):
        """Análisis general de cartera"""
        return """
        SELECT
            COUNT(ef.NumeFact) AS Total_Facturas,
            SUM(ef.ValoTota) AS Valor_Total_Facturado,
            COUNT(fe.NumeDocu) AS Facturas_Electronicas,
            COUNT(CASE WHEN fe.NumeDocu IS NULL THEN 1 END) AS Sin_Factura_Electronica,
            ROUND(AVG(ef.ValoTota), 0) AS Valor_Promedio_Factura,
            SUM(CASE WHEN ef.ValoTota > 1000000 THEN ef.ValoTota ELSE 0 END) AS Valor_Facturas_Altas
        FROM EncaFact ef
        LEFT JOIN FactElec fe ON fe.CodiInst = ef.CodiInst
            AND fe.CodiAno = ef.CodiAno
            AND fe.NumeDocu = ef.NumeFact
            AND fe.CodiDocu = 'FE'
        WHERE ef.FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND ef.Anulado = 0
        """
    
    def get_indicadores_recaudo(self):
        """Indicadores de recaudo por servicio"""
        return """
        SELECT 
            COALESCE(cs.NombServ, ef.CodiServ, 'Sin Definir') as Servicio,
            COUNT(*) as Total_Facturas,
            SUM(ef.ValoTota) as Valor_Total,
            ROUND(AVG(ef.ValoTota), 0) as Valor_Promedio
        FROM EncaFact ef
        LEFT JOIN CodiServ cs ON ef.CodiServ = cs.CodiServ
        WHERE ef.FechFact BETWEEN :fecha_inicio AND :fecha_fin
            AND ef.Anulado = 0
            AND ef.CodiServ IS NOT NULL
            AND ef.CodiServ != ''
        GROUP BY ef.CodiServ, cs.NombServ
        ORDER BY Valor_Total DESC
        """
    
    # ========================================================================
    # PROCEDIMIENTOS
    # ========================================================================
    
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
    
    def get_estadisticas_procedimientos(self):
        """Estadísticas de procedimientos"""
        return """
        SELECT 
            COUNT(*) as Total_Procedimientos,
            COUNT(DISTINCT CodiServ) as Servicios_Activos,
            COUNT(DISTINCT ConsAdmi) as Pacientes_Atendidos,
            ROUND(COUNT(*) / NULLIF(DATEDIFF(:fecha_fin, :fecha_inicio), 0), 1) as Promedio_Por_Dia
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
    
    def get_procedimientos_por_turno(self):
        """Distribución por turno"""
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
                ELSE 3
            END
        """
    
    def get_procedimientos_por_estado(self):
        """Distribución por estado (Realizado/Pendiente)"""
        return """
        SELECT 
            CASE 
                WHEN ProcReal = 1 THEN 'Realizado'
                WHEN ProcReal = 0 THEN 'Pendiente'
                ELSE 'Sin Definir'
            END as Estado,
            COUNT(*) as Total
        FROM HojaProc
        WHERE FechProc BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY ProcReal
        ORDER BY Total DESC
        """
    
    def get_procedimientos_por_profesional(self):
        """Top profesionales que realizan procedimientos"""
        return """
        SELECT 
            COALESCE(u.Nombre, hp.CodiProf, 'Sin Asignar') as Profesional,
            COUNT(*) as Total_Procedimientos
        FROM HojaProc hp
        LEFT JOIN Usuarios u ON hp.CodiProf = u.Login
        WHERE hp.FechProc BETWEEN :fecha_inicio AND :fecha_fin
            AND hp.CodiProf IS NOT NULL
            AND hp.CodiProf != ''
        GROUP BY hp.CodiProf, u.Nombre
        ORDER BY Total_Procedimientos DESC
        LIMIT 15
        """
    
    def get_procedimientos(self):
        """Procedimientos realizados"""
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
        """
    
    def get_procedimientos_por_hora(self):
        """Distribución por hora - ALIAS para turno"""
        return self.get_procedimientos_por_turno()
    
    def get_tendencia_semanal_procedimientos(self):
        """Tendencia últimos 7 días"""
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
    
    def get_tiempos_espera_procedimientos(self):
        """Tiempo promedio entre fecha de la orden (EncaOrde) y realización (HojaProc).
        Usa ConsAdmi + CodiModu como enlace cuando NumeOrde no está disponible."""
        return """
    SELECT
        COALESCE(cs.NombServ, hp.CodiServ, 'Sin Definir') AS Servicio,
        COUNT(*)                                            AS Total_Procedimientos,
        ROUND(AVG(
            DATEDIFF(hp.FechProc, eo.Fecha)
        ), 1)                                               AS Promedio_Dias_Espera,
        MIN(DATEDIFF(hp.FechProc, eo.Fecha))               AS MinDias,
        MAX(DATEDIFF(hp.FechProc, eo.Fecha))               AS MaxDias
    FROM HojaProc hp
    JOIN (
        SELECT ConsAdmi, MIN(Fecha) AS Fecha, CodiModu
        FROM EncaOrde
        GROUP BY ConsAdmi, CodiModu
    ) eo ON eo.ConsAdmi = hp.ConsAdmi
    LEFT JOIN CodiServ cs ON cs.CodiServ = hp.CodiServ
    WHERE hp.FechProc BETWEEN :fecha_inicio AND :fecha_fin
      AND hp.ProcReal = 1
      AND DATEDIFF(hp.FechProc, eo.Fecha) >= 0
      AND DATEDIFF(hp.FechProc, eo.Fecha) <= 30
    GROUP BY hp.CodiServ, cs.NombServ
    HAVING Total_Procedimientos > 5
    ORDER BY Promedio_Dias_Espera DESC
    LIMIT 20
    """

    def get_admisiones_abiertas(self):
        """Admisiones con cama asignada que siguen abiertas (sin fecha de egreso).
        Filtradas por fecha de ingreso y servicio actual."""
        return """
    SELECT
        a.ConsAdmi,
        CASE a.TipoAten
            WHEN 1 THEN 'Consulta Externa'
            WHEN 2 THEN 'Hospitalización'
            WHEN 3 THEN 'Urgencias'
            WHEN 4 THEN 'PyP'
            ELSE CONCAT('Tipo ', a.TipoAten)
        END                                         AS TipoAtencion,
        COALESCE(cs_ing.NombServ, a.CodiServ)       AS ServicioIngreso,
        COALESCE(cs_act.NombServ, a.ServEgre)       AS ServicioActual,
        c.CodiCama,
        c.NombCama,
        a.DiagIngr                                  AS Diagnostico,
        COALESCE(p.NombUsua, a.NumeUsua)            AS Paciente,
        a.FechIngr                                  AS FechaIngreso,
        a.HoraIngr                                  AS HoraIngreso,
        COALESCE(u1.Nombre, a.UsuaDigi)             AS QuienAbrio,
        COALESCE(u2.Nombre, a.UsuaModi)             AS ResponsableCierre,
        a.FechModi                                  AS UltimaModificacion,
        DATEDIFF(CURDATE(), a.FechIngr)             AS DiasAbierta
    FROM Admision a
    JOIN CodiCama c
        ON  c.ConsAdmi = a.ConsAdmi
        AND c.Activa   = 1
    LEFT JOIN CodiServ cs_ing ON cs_ing.CodiServ = a.CodiServ
    LEFT JOIN CodiServ cs_act ON cs_act.CodiServ = a.ServEgre
    LEFT JOIN Paciente p      ON p.NumeUsua = a.NumeUsua
    LEFT JOIN Usuarios u1     ON u1.Login   = a.UsuaDigi
    LEFT JOIN Usuarios u2     ON u2.Login   = a.UsuaModi
    WHERE a.Cerrado  = 2
      AND a.Anulado  = 2
      AND (a.FechEgre IS NULL OR a.FechEgre = '0000-00-00')
    ORDER BY a.FechIngr ASC
    """

    # ========================================================================
    # CIRUGÍAS
    # ========================================================================
    
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
                WHEN 4 THEN 'Sedación'
                ELSE 'Sin Especificar'
            END as Tipo_Anestesia,
            COUNT(*) as Total
        FROM ActoQuir
        WHERE FechInic BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY TipoAnes
        ORDER BY Total DESC
        """
    
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
        """Distribución por hora del día"""
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
        """Distribución por día de la semana"""
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
    
    def get_cirugias_por_especialidad(self):
        """Distribución por especialidad del cirujano"""
        return """
        SELECT 
            COALESCE(ce.NombEspe, 'Sin Especialidad') as Especialidad,
            COUNT(*) as Total_Cirugias
        FROM ActoQuir aq
        INNER JOIN Usuarios u ON aq.UsuaDigi = u.Login
        LEFT JOIN CodiEspe ce ON u.CodiEspe = ce.CodiEspe
        WHERE aq.FechInic BETWEEN :fecha_inicio AND :fecha_fin
            AND aq.UsuaDigi IS NOT NULL
        GROUP BY ce.NombEspe
        ORDER BY Total_Cirugias DESC
        LIMIT 15
        """
    
    def get_cirugias_por_duracion(self):
        """Distribución por rango de duración"""
        return """
        SELECT 
            CASE 
                WHEN TIMESTAMPDIFF(MINUTE, HoraInic, HoraFina) < 60 THEN 'Menos de 1 hora'
                WHEN TIMESTAMPDIFF(MINUTE, HoraInic, HoraFina) < 120 THEN '1-2 horas'
                WHEN TIMESTAMPDIFF(MINUTE, HoraInic, HoraFina) < 180 THEN '2-3 horas'
                ELSE 'Más de 3 horas'
            END as Rango_Duracion,
            COUNT(*) as Total
        FROM ActoQuir
        WHERE FechInic BETWEEN :fecha_inicio AND :fecha_fin
            AND HoraInic IS NOT NULL
            AND HoraFina IS NOT NULL
            AND HoraFina > HoraInic
        GROUP BY Rango_Duracion
        ORDER BY 
            CASE Rango_Duracion
                WHEN 'Menos de 1 hora' THEN 1
                WHEN '1-2 horas' THEN 2
                WHEN '2-3 horas' THEN 3
                ELSE 4
            END
        """
    
    def get_top_procedimientos_quirurgicos(self):
        """Top diagnósticos post-operatorios"""
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
    def get_analisis_duracion_cirugias(self):
        """Análisis detallado de duración de cirugías"""
        return """
        SELECT 
            COALESCE(ce.NombEspe, 'Sin Especialidad') as Especialidad, 
            COUNT(*) as Total_Cirugias, 
            ROUND(AVG(TIMESTAMPDIFF(MINUTE, CONCAT(FechInic, ' ', HoraInic), CONCAT(FechFina, ' ', HoraFina))), 0) as Duracion_Promedio_Min, 
            ROUND(MIN(TIMESTAMPDIFF(MINUTE, CONCAT(FechInic, ' ', HoraInic), CONCAT(FechFina, ' ', HoraFina))), 0) as Duracion_Minima, 
            ROUND(MAX(TIMESTAMPDIFF(MINUTE, CONCAT(FechInic, ' ', HoraInic), CONCAT(FechFina, ' ', HoraFina))), 0) as Duracion_Maxima, 
            ROUND(STD(TIMESTAMPDIFF(MINUTE, CONCAT(FechInic, ' ', HoraInic), CONCAT(FechFina, ' ', HoraFina))), 0) as Desviacion_Estandar 
        FROM ActoQuir aq 
        -- Cambio de MediCiru a UsuaDigi según tu hallazgo
        LEFT JOIN Usuarios u ON aq.UsuaDigi = u.Login 
        LEFT JOIN CodiEspe ce ON u.CodiEspe = ce.CodiEspe 
        WHERE aq.FechInic BETWEEN :fecha_inicio AND :fecha_fin
        GROUP BY ce.NombEspe, u.CodiEspe
        HAVING Total_Cirugias > 3 
        ORDER BY Total_Cirugias DESC
        """

    def get_distribucion_duracion(self):
        """Distribución de cirugías por duración"""
        return """
        SELECT 
            CASE 
                WHEN TIMESTAMPDIFF(MINUTE, 
                    CONCAT(FechInic, ' ', HoraInic),
                    CONCAT(FechFina, ' ', HoraFina)
                ) < 30 THEN 'Menos de 30 min'
                WHEN TIMESTAMPDIFF(MINUTE, 
                    CONCAT(FechInic, ' ', HoraInic),
                    CONCAT(FechFina, ' ', HoraFina)
                ) < 60 THEN '30-60 min'
                WHEN TIMESTAMPDIFF(MINUTE, 
                    CONCAT(FechInic, ' ', HoraInic),
                    CONCAT(FechFina, ' ', HoraFina)
                ) < 120 THEN '1-2 horas'
                WHEN TIMESTAMPDIFF(MINUTE, 
                    CONCAT(FechInic, ' ', HoraInic),
                    CONCAT(FechFina, ' ', HoraFina)
                ) < 180 THEN '2-3 horas'
                ELSE 'Más de 3 horas'
            END as Rango_Duracion,
            COUNT(*) as Total_Cirugias
        FROM ActoQuir
        WHERE FechInic BETWEEN :fecha_inicio AND :fecha_fin
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
    # ========================================================================
    # OCUPACIÓN
    # ========================================================================
    
    def get_ocupacion_actual(self):
        """Ocupación actual de camas"""
        return """
        SELECT
            COUNT(c.CodiCama) AS Total_Camas,
            COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) AS Ocupadas,
            COUNT(c.CodiCama) - COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) AS Libres,
            ROUND(
                COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) * 100.0
                / NULLIF(COUNT(c.CodiCama), 0), 1
            ) AS Porcentaje_Ocupacion
        FROM CodiCama c
        LEFT JOIN Admision a ON a.ConsAdmi = c.ConsAdmi
        WHERE c.Activa = 1 AND c.Habilita = 1
        """
    
    def get_ocupacion_general(self):
        """Ocupación general de camas"""
        return self.get_ocupacion_actual()
    
    def get_ocupacion_por_servicio(self):
        """Ocupación por servicio"""
        return """
        SELECT
            COALESCE(cs.NombServ, c.CodiServ, 'Sin Servicio') AS Servicio,
            COUNT(c.CodiCama) AS Total_Camas,
            COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) AS Ocupadas,
            ROUND(
                COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) * 100.0
                / NULLIF(COUNT(c.CodiCama), 0), 1
            ) AS Porcentaje_Ocupacion
        FROM CodiCama c
        LEFT JOIN Admision a ON a.ConsAdmi = c.ConsAdmi
        LEFT JOIN CodiServ cs ON cs.CodiServ = c.CodiServ
        WHERE c.Activa = 1 AND c.Habilita = 1
            AND c.CodiServ IS NOT NULL
            AND c.CodiServ != ''
        GROUP BY c.CodiServ, cs.NombServ
        ORDER BY Ocupadas DESC
        """
    
    def get_historico_ocupacion(self):
        """Ocupación últimos 7 días"""
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
                AND (NULLIF(a.FechEgre, '0000-00-00') >= fechas.Fecha OR NULLIF(a.FechEgre, '0000-00-00') IS NULL)
                AND a.Cerrado = 2
            WHERE c.Activa = 1
            GROUP BY fechas.Fecha
        ) datos
        ORDER BY Fecha
        """
    
    def get_rotacion_camas(self):
        """Rotación de camas últimos 30 días"""
        return """
        SELECT 
            c.CodiCama,
            c.NombCama,
            COUNT(DISTINCT a.ConsAdmi) as Veces_Usada,
            ROUND(AVG(DATEDIFF(
                COALESCE(NULLIF(a.FechEgre, '0000-00-00'), CURDATE()),
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
        """Distribución por tipo de cama"""
        return """
        SELECT
            COALESCE(c.TipoCama, 'Sin Tipo') AS Tipo,
            COUNT(c.CodiCama) AS Total,
            COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) AS Ocupadas
        FROM CodiCama c
        LEFT JOIN Admision a ON a.ConsAdmi = c.ConsAdmi
        WHERE c.Activa = 1 AND c.Habilita = 1
        GROUP BY c.TipoCama
        ORDER BY Total DESC
        """
    
    def get_ocupacion_por_uci(self):
        """Distribución UCI vs No-UCI"""
        return """
        SELECT
            CASE WHEN c.EsUci = 1 THEN 'UCI' ELSE 'No UCI' END AS Tipo,
            COUNT(c.CodiCama) AS Total,
            COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) AS Ocupadas,
            ROUND(
                COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) * 100.0
                / NULLIF(COUNT(c.CodiCama), 0), 1
            ) AS Porcentaje_Ocupacion
        FROM CodiCama c
        LEFT JOIN Admision a ON a.ConsAdmi = c.ConsAdmi
        WHERE c.Activa = 1 AND c.Habilita = 1
        GROUP BY c.EsUci
        ORDER BY Total DESC
        """
    
    def get_alertas_ocupacion(self):
        """Alertas de ocupación por servicio"""
        return """
        SELECT
            COALESCE(cs.NombServ, c.CodiServ, 'Sin Servicio') AS Servicio,
            COUNT(c.CodiCama) AS Total_Camas,
            COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) AS Ocupadas,
            ROUND(
                COUNT(CASE WHEN a.Cerrado = 2 AND a.Anulado = 2 AND a.FechEgre IS NULL THEN 1 END) * 100.0
                / NULLIF(COUNT(c.CodiCama), 0), 1
            ) AS Porcentaje_Ocupacion
        FROM CodiCama c
        LEFT JOIN Admision a ON a.ConsAdmi = c.ConsAdmi
        LEFT JOIN CodiServ cs ON cs.CodiServ = c.CodiServ
        WHERE c.Activa = 1 AND c.Habilita = 1
            AND c.CodiServ IS NOT NULL
            AND c.CodiServ != ''
        GROUP BY c.CodiServ, cs.NombServ
        HAVING COUNT(c.CodiCama) > 0
        ORDER BY Porcentaje_Ocupacion DESC
        LIMIT 10
        """
    
    # ========================================================================
    # PROFESIONALES
    # ========================================================================
    
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
            COALESCE(u.Nombre, rc.UsuaCons) as Profesional,
            COUNT(*) as Total_Atenciones
        FROM RipsCons rc
        LEFT JOIN Usuarios u ON rc.UsuaCons = u.Login
        WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND rc.UsuaCons IS NOT NULL
            AND rc.UsuaCons != ''
        GROUP BY rc.UsuaCons, u.Nombre
        ORDER BY Total_Atenciones DESC
        LIMIT 20
        """
    
    def get_distribucion_carga_profesionales(self):
        """Distribución de carga de trabajo"""
        return """
        SELECT 
            COALESCE(u.Nombre, rc.UsuaCons) as Profesional,
            COUNT(*) as Total_Atenciones,
            ROUND((COUNT(*) / (SELECT COUNT(*) FROM RipsCons WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin)) * 100, 1) as Porcentaje_Carga
        FROM RipsCons rc
        LEFT JOIN Usuarios u ON rc.UsuaCons = u.Login
        WHERE rc.FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND rc.UsuaCons IS NOT NULL
            AND rc.UsuaCons != ''
        GROUP BY rc.UsuaCons, u.Nombre
        ORDER BY Total_Atenciones DESC
        LIMIT 15
        """
    
    def get_productividad_profesionales(self):
        """Productividad de profesionales"""
        return """
        SELECT 
            COALESCE(u.Nombre, rc.UsuaCons) as Profesional,
            COUNT(*) as Total_Atenciones,
            COUNT(CASE WHEN rc.EstaReal = 1 THEN 1 END) as Realizadas,
            COUNT(CASE WHEN rc.EstaReal = 0 THEN 1 END) as Pendientes,
            ROUND((COUNT(CASE WHEN rc.EstaReal = 1 THEN 1 END) / COUNT(*)) * 100, 1) as Porcentaje_Cumplimiento
        FROM RipsCons rc
        LEFT JOIN Usuarios u ON rc.UsuaCons = u.Login
        WHERE rc.FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND rc.UsuaCons IS NOT NULL
            AND rc.UsuaCons != ''
        GROUP BY rc.UsuaCons, u.Nombre
        HAVING COUNT(*) >= 5
        ORDER BY Realizadas DESC
        LIMIT 15
        """
    
    def get_atenciones_por_servicio(self):
        """Atenciones por servicio"""
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
    
    def get_atenciones_por_especialidad(self):
        """Atenciones por especialidad"""
        return """
        SELECT 
            COALESCE(ce.NombEspe, 'Sin Especialidad') as Especialidad,
            COUNT(*) as Total_Atenciones
        FROM RipsCons rc
        LEFT JOIN CodiEspe ce ON rc.CodiEspe = ce.CodiEspe
        WHERE rc.FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND rc.CodiEspe IS NOT NULL
        GROUP BY rc.CodiEspe, ce.NombEspe
        ORDER BY Total_Atenciones DESC
        LIMIT 15
        """
    
    def get_atenciones_por_turno_profesional(self):
        """Atenciones por turno"""
        return """
        SELECT
            CASE
                WHEN HOUR(rc.HoraCons) >= 6 AND HOUR(rc.HoraCons) < 14 THEN 'Mañana (6am-2pm)'
                WHEN HOUR(rc.HoraCons) >= 14 AND HOUR(rc.HoraCons) < 22 THEN 'Tarde (2pm-10pm)'
                ELSE 'Noche (10pm-6am)'
            END as Turno,
            COUNT(*) as Total_Atenciones
        FROM RipsCons rc
        WHERE rc.FechCons BETWEEN :fecha_inicio AND :fecha_fin
            AND rc.HoraCons IS NOT NULL
        GROUP BY Turno
        ORDER BY
            CASE Turno
                WHEN 'Mañana (6am-2pm)' THEN 1
                WHEN 'Tarde (2pm-10pm)' THEN 2
                ELSE 3
            END
        """

    # ========================================================================
    # CITAS
    # ========================================================================

    def get_estadisticas_citas(self):
        """Métricas globales de citas — solo estados válidos 1-7"""
        return """
        SELECT
            COUNT(*) AS Total_Citas,
            COUNT(CASE WHEN EstaCita = 1 THEN 1 END) AS Disponibles,
            COUNT(CASE WHEN EstaCita = 2 THEN 1 END) AS Ocupadas,
            COUNT(CASE WHEN EstaCita = 3 THEN 1 END) AS Cumplidas,
            COUNT(CASE WHEN EstaCita IN (4, 5, 7) THEN 1 END) AS Incumplidas,
            COUNT(CASE WHEN EstaCita = 6 THEN 1 END) AS Canceladas
        FROM DetaCita
        WHERE FechCita BETWEEN :fecha_inicio AND :fecha_fin
          AND EstaCita BETWEEN 1 AND 7
        """

    def get_distribucion_estado_citas(self):
        """Distribución por estado de cita con porcentaje (EstaCita 1-7 únicamente)"""
        return """
        SELECT
            ec.NombEsta AS Estado,
            COUNT(*) AS TotalCitas,
            ROUND(
                COUNT(*) * 100.0 / (
                    SELECT COUNT(*) FROM DetaCita
                    WHERE FechCita BETWEEN :fecha_inicio AND :fecha_fin
                      AND EstaCita BETWEEN 1 AND 7
                ), 2
            ) AS Porcentaje
        FROM DetaCita dc
        JOIN EstaCita ec ON ec.CodiEsta = dc.EstaCita
        WHERE dc.FechCita BETWEEN :fecha_inicio AND :fecha_fin
          AND dc.EstaCita BETWEEN 1 AND 7
        GROUP BY ec.NombEsta
        ORDER BY TotalCitas DESC
        """

    def get_oportunidad_espera_solicitud(self):
        """KPI 1 — Días entre solicitud (FechSoli) y fecha de cita.
        Filtro por FechSoli en el rango. Valor esperado ~2.5 días.
        PENDIENTE validación contra SIHOS nativo (29.66 días reportados)."""
        return """
        SELECT
            ROUND(AVG(DATEDIFF(FechCita, FechSoli)), 2) AS PromEsperaSolicitud,
            COUNT(*) AS TotalCitas
        FROM DetaCita
        WHERE FechSoli BETWEEN :fecha_inicio AND :fecha_fin
          AND EstaCita BETWEEN 1 AND 7
          AND DATEDIFF(FechCita, FechSoli) >= 0
        """

    def get_oportunidad_espera_asignacion(self):
        """KPI 2 — Días entre asignación (FechAsig) y fecha de cita.
        Filtro por FechCita en el rango. Validado vs SIHOS nativo: ~8.7 días (SIHOS: 7.92 días)."""
        return """
        SELECT
            ROUND(AVG(DATEDIFF(FechCita, FechAsig)), 2) AS PromEsperaAsignacion,
            COUNT(*) AS TotalCitas
        FROM DetaCita
        WHERE FechCita BETWEEN :fecha_inicio AND :fecha_fin
          AND EstaCita BETWEEN 1 AND 7
          AND DATEDIFF(FechCita, FechAsig) >= 0
        """

    # ========================================================================
    # INTEROPERABILIDAD RDA
    # ========================================================================

    def get_rda_summary_hoy(self):
        """Resumen RDA del día actual (para home)"""
        return """
        SELECT
            SUM(CASE WHEN estado_id = 56 THEN 1 ELSE 0 END) AS Enviados,
            SUM(CASE WHEN estado_id = 57 THEN 1 ELSE 0 END) AS Pendientes,
            SUM(CASE WHEN estado_id = 58 THEN 1 ELSE 0 END) AS Rechazados,
            COUNT(*) AS Total
        FROM EnviRda
        WHERE deleted_at IS NULL
          AND DATE(created_at) = CURDATE()
        """

    def get_rda_summary(self):
        """Resumen RDA para rango de fechas (para reportes)"""
        return """
        SELECT
            SUM(CASE WHEN estado_id = 56 THEN 1 ELSE 0 END) AS Enviados,
            SUM(CASE WHEN estado_id = 57 THEN 1 ELSE 0 END) AS Pendientes,
            SUM(CASE WHEN estado_id = 58 THEN 1 ELSE 0 END) AS Rechazados,
            COUNT(*) AS Total
        FROM EnviRda
        WHERE deleted_at IS NULL
          AND DATE(created_at) BETWEEN :fecha_inicio AND :fecha_fin
        """

    def get_rda_tabla(self, estado_id=None, busqueda=None):
        """Tabla principal RDA — pivotada por admisión con estado de cada tipo RDA"""
        filtro_estado = "AND e.estado_id = :estado_id" if estado_id is not None else ""
        filtro_busqueda = "AND e.ConsAdmi LIKE :busqueda" if busqueda else ""
        return f"""
        SELECT
            e.ConsAdmi                          AS Admision,
            COALESCE(p.NombUsua, 'Sin datos')   AS Paciente,
            DATE(MIN(e.created_at))             AS Reportado,
            MAX(CASE WHEN e.tipo_rda_id = 60
                THEN CASE e.estado_id
                    WHEN 56 THEN '🟢 Enviado'
                    WHEN 57 THEN '🟡 Pendiente'
                    WHEN 58 THEN '🔴 Rechazado'
                END END)                        AS RDA_Paciente,
            MAX(CASE WHEN e.tipo_rda_id = 61
                THEN CASE e.estado_id
                    WHEN 56 THEN '🟢 Enviado'
                    WHEN 57 THEN '🟡 Pendiente'
                    WHEN 58 THEN '🔴 Rechazado'
                END END)                        AS RDA_ConsExterna,
            'No Aplica'                         AS RDA_Urg,
            'No Aplica'                         AS RDA_Hosp,
            MAX(e.updated_at)                   AS UltimaActualizacion
        FROM EnviRda e
        LEFT JOIN Admision a ON a.ConsAdmi = e.ConsAdmi
        LEFT JOIN Paciente p ON p.NumeUsua = a.NumeUsua
        WHERE e.deleted_at IS NULL
          AND DATE(e.created_at) BETWEEN :fecha_inicio AND :fecha_fin
          {filtro_estado}
          {filtro_busqueda}
        GROUP BY e.ConsAdmi, p.NombUsua
        ORDER BY MAX(e.created_at) DESC
        LIMIT 500
        """

    # ========================================================================
    # RESOLUCIÓN 373 — TIEMPOS DE ESPERA URGENCIAS
    # ========================================================================

    def get_373_kpis(self):
        """KPIs generales de tiempos de espera urgencias para Resolución 373"""
        return """
    SELECT
        COUNT(*)                                                    AS TotalUrgencias,
        ROUND(AVG(TIMESTAMPDIFF(MINUTE, a.HoraIngr, t.HoraTria)),1) AS PromEsperaMin,
        MIN(TIMESTAMPDIFF(MINUTE, a.HoraIngr, t.HoraTria))         AS MinEsperaMin,
        MAX(TIMESTAMPDIFF(MINUTE, a.HoraIngr, t.HoraTria))         AS MaxEsperaMin,
        SUM(CASE WHEN TIMESTAMPDIFF(MINUTE,a.HoraIngr,t.HoraTria) <= 30  THEN 1 ELSE 0 END) AS DentroStd,
        SUM(CASE WHEN TIMESTAMPDIFF(MINUTE,a.HoraIngr,t.HoraTria) > 30   THEN 1 ELSE 0 END) AS FueraStd
    FROM Triage t
    JOIN Admision a ON a.ConsAdmi = t.ConsAdmi
    WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
      AND a.TipoAten = 3
      AND a.Anulado  = 2
      AND TIMESTAMPDIFF(MINUTE, a.HoraIngr, t.HoraTria) >= 0
    """

    def get_373_por_triage(self):
        """Tiempo de espera por clasificación de triage con semáforo vs estándar"""
        return """
    SELECT
        t.ClasTria,
        CASE t.ClasTria
            WHEN 1 THEN '1 - Reanimación'
            WHEN 2 THEN '2 - Emergencia'
            WHEN 3 THEN '3 - Urgencia'
            WHEN 4 THEN '4 - Menos urgente'
            WHEN 5 THEN '5 - No urgente'
        END                                                             AS NivelTriage,
        COUNT(*)                                                        AS Total,
        ROUND(AVG(TIMESTAMPDIFF(MINUTE,a.HoraIngr,t.HoraTria)),1)      AS PromEsperaMin,
        MAX(TIMESTAMPDIFF(MINUTE,a.HoraIngr,t.HoraTria))               AS MaxEsperaMin,
        CASE t.ClasTria
            WHEN 1 THEN 0
            WHEN 2 THEN 30
            WHEN 3 THEN 60
            WHEN 4 THEN 120
            WHEN 5 THEN 240
        END                                                             AS LimiteStdMin
    FROM Triage t
    JOIN Admision a ON a.ConsAdmi = t.ConsAdmi
    WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
      AND a.TipoAten = 3
      AND a.Anulado  = 2
      AND TIMESTAMPDIFF(MINUTE, a.HoraIngr, t.HoraTria) >= 0
    GROUP BY t.ClasTria
    ORDER BY t.ClasTria
    """

    def get_373_por_causa(self):
        """Tiempo de espera por causa externa"""
        return """
    SELECT
        COALESCE(ce.NombMoti, CONCAT('Causa ', a.CausExte)) AS CausaExterna,
        COUNT(*)                                             AS Total,
        ROUND(AVG(TIMESTAMPDIFF(MINUTE,a.HoraIngr,t.HoraTria)),1) AS PromEsperaMin
    FROM Triage t
    JOIN Admision a  ON a.ConsAdmi  = t.ConsAdmi
    LEFT JOIN CausExte ce ON ce.CodiMoti = a.CausExte
    WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
      AND a.TipoAten = 3
      AND a.Anulado  = 2
      AND a.CausExte IS NOT NULL
      AND a.CausExte != ''
      AND TIMESTAMPDIFF(MINUTE, a.HoraIngr, t.HoraTria) >= 0
    GROUP BY a.CausExte, ce.NombMoti
    ORDER BY Total DESC
    LIMIT 10
    """

    def get_373_por_servicio(self):
        """Tiempo de espera por servicio de urgencias"""
        return """
    SELECT
        COALESCE(cs.NombServ, a.CodiServ)                   AS Servicio,
        COUNT(*)                                             AS Total,
        ROUND(AVG(TIMESTAMPDIFF(MINUTE,a.HoraIngr,t.HoraTria)),1) AS PromEsperaMin,
        MAX(TIMESTAMPDIFF(MINUTE,a.HoraIngr,t.HoraTria))    AS MaxEsperaMin
    FROM Triage t
    JOIN Admision a  ON a.ConsAdmi  = t.ConsAdmi
    LEFT JOIN CodiServ cs ON cs.CodiServ = a.CodiServ
    WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
      AND a.TipoAten = 3
      AND a.Anulado  = 2
      AND TIMESTAMPDIFF(MINUTE, a.HoraIngr, t.HoraTria) >= 0
    GROUP BY a.CodiServ, cs.NombServ
    ORDER BY PromEsperaMin DESC
    """

    def get_373_tendencia_diaria(self):
        """Tendencia diaria de tiempo de espera urgencias"""
        return """
    SELECT
        a.FechIngr                                               AS Fecha,
        COUNT(*)                                                 AS TotalUrgencias,
        ROUND(AVG(TIMESTAMPDIFF(MINUTE,a.HoraIngr,t.HoraTria)),1) AS PromEsperaMin
    FROM Triage t
    JOIN Admision a ON a.ConsAdmi = t.ConsAdmi
    WHERE a.FechIngr BETWEEN :fecha_inicio AND :fecha_fin
      AND a.TipoAten = 3
      AND a.Anulado  = 2
      AND TIMESTAMPDIFF(MINUTE, a.HoraIngr, t.HoraTria) >= 0
    GROUP BY a.FechIngr
    ORDER BY Fecha
    """

    def get_atenciones_por_modulo(self):
        """Distribución de atenciones por módulo clínico (más granular que TipoAten)"""
        return """
    SELECT
        CASE CodiModu
            WHEN 5  THEN 'Consulta Externa'
            WHEN 6  THEN 'Urgencias'
            WHEN 8  THEN 'Hospitalización/UCI'
            WHEN 9  THEN 'Odontología'
            WHEN 10 THEN 'Laboratorio'
            WHEN 15 THEN 'PyP'
            WHEN 27 THEN 'Cirugía'
            WHEN 28 THEN 'Procedimientos'
            WHEN 38 THEN 'Terapias'
            ELSE CONCAT('Módulo ', CodiModu)
        END                         AS Modulo,
        COUNT(*)                    AS Total_Atenciones,
        COUNT(DISTINCT UsuaCons)    AS Profesionales_Activos,
        COUNT(CASE WHEN EstaReal = 1 THEN 1 END) AS Realizadas,
        ROUND(
            COUNT(CASE WHEN EstaReal = 1 THEN 1 END) * 100.0
            / NULLIF(COUNT(*), 0), 1
        )                           AS PctCumplimiento
    FROM RipsCons
    WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
      AND UsuaCons IS NOT NULL
      AND UsuaCons != ''
    GROUP BY CodiModu
    ORDER BY Total_Atenciones DESC
    """

    def get_heatmap_hora_profesional(self):
        """Distribución de atenciones por hora del día y día de la semana"""
        return """
    SELECT
        HOUR(HoraCons)      AS Hora,
        DAYOFWEEK(FechCons) AS DiaSemana,
        CASE DAYOFWEEK(FechCons)
            WHEN 1 THEN 'Dom'
            WHEN 2 THEN 'Lun'
            WHEN 3 THEN 'Mar'
            WHEN 4 THEN 'Mié'
            WHEN 5 THEN 'Jue'
            WHEN 6 THEN 'Vie'
            WHEN 7 THEN 'Sáb'
        END                 AS NombreDia,
        COUNT(*)            AS Total
    FROM RipsCons
    WHERE FechCons BETWEEN :fecha_inicio AND :fecha_fin
      AND HoraCons IS NOT NULL
      AND HoraCons != '00:00:00'
      AND UsuaCons IS NOT NULL
      AND UsuaCons != ''
    GROUP BY HOUR(HoraCons), DAYOFWEEK(FechCons)
    ORDER BY DiaSemana, Hora
    """

    def get_rda_detalle(self):
        """Detalle de envíos RDA por admisión. JSON parseado en Python (sin permisos JSON_UNQUOTE)."""
        return """
    SELECT
        e.id                AS EnviRda_id,
        e.ConsAdmi,
        CASE e.tipo_rda_id
            WHEN 60 THEN 'RDA Paciente'
            WHEN 61 THEN 'RDA Consulta Externa'
            ELSE CONCAT('Tipo ', e.tipo_rda_id)
        END                 AS TipoRDA,
        CASE e.estado_id
            WHEN 56 THEN '🟢 Enviado'
            WHEN 57 THEN '🟡 Pendiente'
            WHEN 58 THEN '🔴 Rechazado'
        END                 AS Estado,
        e.usuario           AS UsuarioSIHOS,
        e.created_at        AS FechaEnvio,
        a.json_respuesta    AS JsonRespuesta,
        a.created_at        AS FechaRespuesta
    FROM EnviRda e
    LEFT JOIN AudiRda a ON a.EnviRda_id = e.id
    WHERE e.ConsAdmi = :consadmi
      AND e.deleted_at IS NULL
    ORDER BY e.tipo_rda_id, a.created_at DESC
    """

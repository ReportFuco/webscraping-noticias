WITH base_judicial AS (
    SELECT
        TRY_CAST(jud.[1000_PROCEDIMIENTO] AS int)	AS PROCEDIMIENTO,
		-- creación de la llave para convinar con CaseTracking
		(
			CAST(
				CAST(
					jud.[1000_PROCEDIMIENTO] AS int
				) AS varchar) + 
			REPLACE(jud.[1007_ROL_ANO], '|', ''))	AS PROCEDIMIENTO_ROL_KEY,
		
		-- Mas variables necesarias para el reporte
        jud.[1007_ROL_ANO]							AS ROL_ANO,
        jud.[1005_TIPO_PROCEDIMIENTO]				AS TIPO_PROCEDIMIENTO,
        jud.[1006_ESTADO_PROCEDIMIENTO]				AS ESTADO_PROCEDIMIENTO,
        jud.[1012_PRODUCTO]							AS PRODUCTO,
        jud.[1013_SUBPRODUCTO]						AS SUBPRRODUCTO,
		jud.[1022_NOMBRE_ABOGADO_TRAMITADOR]		AS ABOGADO_TRAMITADOR,
		jud.[1020_NOMBRE_SUPERVISOR_SUPERIOR]		AS SUPERVISOR_SUPERIOR,
		jud.[1011_SEGMENTO_CLIENTE]					AS SEGMENTO_CLIENTE -- FILTRAR DENTRO DEL REPORTE BI
    FROM EXPLOTACION.dbo.base_judicial_campanas_v2 jud
    WHERE ISNUMERIC(jud.[1000_PROCEDIMIENTO]) = 1
		AND jud.[1007_ROL_ANO] IS NOT NULL
		AND jud.[1007_ROL_ANO] <> '0|0'

),
Tramites AS (
    SELECT *
    FROM (
        SELECT
            tr.id_procedimiento					AS ID_PROCEDIMIENTO,
            CONVERT(DATE, tr.fecha_alta, 103)	AS FECHA_ALTA,
            tr.hito								AS HITO,
            tr.tipo_tramite						AS TIPO_TRAMITE,
            tr.observacion						AS OBSERVACION,
            ROW_NUMBER() OVER (
                PARTITION BY tr.id_procedimiento
                ORDER BY tr.fecha_alta DESC
            )									AS RANCKING
        FROM EXPLOTACION.dbo.jud_tramites tr
        WHERE tipo_tramite IN (
            'Causa disponible en Casetracking',
            'No es posible conectar Causa en Casetracking'
        )
    ) t
    WHERE RANCKING = 1
)
SELECT *
FROM base_judicial bj
LEFT JOIN Tramites tr 
    ON tr.ID_PROCEDIMIENTO = bj.PROCEDIMIENTO;
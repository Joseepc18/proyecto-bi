-- =====================================================================
-- Consultas Analiticas - Los 6 KPIs (Entregable 4)
-- Cada KPI usa JOINs entre la tabla de hechos y sus dimensiones.
-- Ejecutar cada consulta por separado en pgAdmin (seleccionar y F5).
-- =====================================================================


-- ─────────────────────────────────────────────────────────────────────
-- KPI 1 - Salario promedio por rol
-- Pregunta: cuanto paga en promedio cada rol?
-- ─────────────────────────────────────────────────────────────────────
SELECT
    r.nombre_rol,
    ROUND(AVG(f.salario_ofertado), 2)       AS salario_promedio_usd,
    COUNT(*)                                 AS ofertas_con_salario
FROM fact_ofertas_empleo f
JOIN dim_rol r ON f.id_rol = r.id_rol
WHERE f.tiene_salario = 1
GROUP BY r.nombre_rol
ORDER BY salario_promedio_usd DESC;


-- ─────────────────────────────────────────────────────────────────────
-- KPI 2 - Tasa de ofertas remotas
-- Pregunta: que porcentaje de las ofertas son remotas?
-- ─────────────────────────────────────────────────────────────────────
SELECT
    ROUND(100.0 * SUM(f.es_remota) / COUNT(*), 1) AS tasa_remota_pct,
    SUM(f.es_remota)                              AS ofertas_remotas,
    COUNT(*)                                      AS total_ofertas
FROM fact_ofertas_empleo f;


-- ─────────────────────────────────────────────────────────────────────
-- KPI 3 - Indice de demanda por tecnologia (top 10)
-- Pregunta: cuales son las tecnologias mas demandadas?
-- ─────────────────────────────────────────────────────────────────────
SELECT
    t.nombre_tecnologia,
    COUNT(*)                                                              AS menciones,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_ofertas_empleo), 1) AS indice_demanda_pct
FROM puente_oferta_tecnologia p
JOIN dim_tecnologia t ON p.id_tecnologia = t.id_tecnologia
GROUP BY t.nombre_tecnologia
ORDER BY menciones DESC
LIMIT 10;


-- ─────────────────────────────────────────────────────────────────────
-- KPI 4 - Brecha salarial local vs internacional
-- Pregunta: se gana mas en el extranjero que en Ecuador?
-- ─────────────────────────────────────────────────────────────────────
SELECT
    fu.ambito,
    ROUND(AVG(f.salario_ofertado), 2) AS salario_promedio_usd,
    COUNT(*)                          AS ofertas_con_salario
FROM fact_ofertas_empleo f
JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente
WHERE f.tiene_salario = 1
GROUP BY fu.ambito
ORDER BY salario_promedio_usd DESC;


-- ─────────────────────────────────────────────────────────────────────
-- KPI 5 - Variacion de ofertas por rol (por mes, con funcion de ventana LAG)
-- Pregunta: como crece o cae el numero de ofertas de cada rol?
-- ─────────────────────────────────────────────────────────────────────
SELECT
    r.nombre_rol,
    t.mes,
    t.nombre_mes,
    COUNT(*)                                                          AS ofertas,
    LAG(COUNT(*)) OVER (PARTITION BY r.nombre_rol ORDER BY t.mes)     AS ofertas_mes_anterior
FROM fact_ofertas_empleo f
JOIN dim_rol r    ON f.id_rol    = r.id_rol
JOIN dim_tiempo t ON f.id_tiempo = t.id_tiempo
WHERE r.nombre_rol <> 'Otro'
GROUP BY r.nombre_rol, t.mes, t.nombre_mes
ORDER BY r.nombre_rol, t.mes;


-- ─────────────────────────────────────────────────────────────────────
-- KPI 6 - Relacion salario TI vs salario nacional (INEC)
-- Pregunta: los roles TI ganan mas que el promedio nacional del sector?
-- ─────────────────────────────────────────────────────────────────────
SELECT
    ROUND(AVG(f.salario_ofertado), 2)                              AS salario_promedio_ti,
    MAX(t.salario_promedio_nacional)                               AS salario_nacional_inec,
    ROUND(AVG(f.salario_ofertado) / MAX(t.salario_promedio_nacional), 2) AS relacion_ti_vs_nacional
FROM fact_ofertas_empleo f
JOIN dim_tiempo t ON f.id_tiempo = t.id_tiempo
WHERE f.tiene_salario = 1;

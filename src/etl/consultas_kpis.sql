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
-- Parte A: salario promedio por ambito.
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

-- Parte B: la brecha como porcentaje, segun la formula del E1:
-- ((salario_internacional - salario_local) / salario_local) * 100
WITH prom AS (
    SELECT fu.ambito, AVG(f.salario_ofertado) AS s
    FROM fact_ofertas_empleo f
    JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente
    WHERE f.tiene_salario = 1
    GROUP BY fu.ambito
)
SELECT ROUND(100.0 * (
           MAX(s) FILTER (WHERE ambito = 'internacional')
         - MAX(s) FILTER (WHERE ambito = 'local')
       ) / MAX(s) FILTER (WHERE ambito = 'local'), 1) AS brecha_pct
FROM prom;


-- ─────────────────────────────────────────────────────────────────────
-- KPI 5 - Variacion de ofertas por rol (por mes, con funcion de ventana LAG)
-- Pregunta: como crece o cae el numero de ofertas de cada rol?
-- Se calcula la variacion porcentual segun la formula del E1:
-- ((ofertas_actual - ofertas_anterior) / ofertas_anterior) * 100
-- ─────────────────────────────────────────────────────────────────────
WITH por_mes AS (
    SELECT
        r.nombre_rol,
        t.mes,
        t.nombre_mes,
        COUNT(*)                                                      AS ofertas,
        LAG(COUNT(*)) OVER (PARTITION BY r.nombre_rol ORDER BY t.mes) AS ofertas_mes_anterior
    FROM fact_ofertas_empleo f
    JOIN dim_rol r    ON f.id_rol    = r.id_rol
    JOIN dim_tiempo t ON f.id_tiempo = t.id_tiempo
    WHERE r.nombre_rol <> 'Otro'
    GROUP BY r.nombre_rol, t.mes, t.nombre_mes
)
SELECT
    nombre_rol,
    nombre_mes,
    ofertas,
    ofertas_mes_anterior,
    ROUND(100.0 * (ofertas - ofertas_mes_anterior)
          / NULLIF(ofertas_mes_anterior, 0), 1) AS variacion_pct
FROM por_mes
ORDER BY nombre_rol, mes;


-- ─────────────────────────────────────────────────────────────────────
-- KPI 6 - Relacion salario TI vs salario nacional (INEC)
-- Pregunta: los roles TI en Ecuador ganan mas que el promedio nacional del sector?
-- Se compara SOLO el salario LOCAL (Ecuador) contra el promedio nacional del INEC,
-- que tambien es de Ecuador: comparar Ecuador vs Ecuador es lo coherente. El salario
-- internacional se analiza aparte en el KPI 4 (brecha), no aqui.
-- ─────────────────────────────────────────────────────────────────────
SELECT
    ROUND(AVG(f.salario_ofertado), 2)                              AS salario_promedio_ti_local,
    MAX(t.salario_promedio_nacional)                               AS salario_nacional_inec,
    ROUND(AVG(f.salario_ofertado) / MAX(t.salario_promedio_nacional), 2) AS relacion_ti_vs_nacional
FROM fact_ofertas_empleo f
JOIN dim_tiempo t  ON f.id_tiempo = t.id_tiempo
JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente
WHERE f.tiene_salario = 1 AND fu.ambito = 'local';

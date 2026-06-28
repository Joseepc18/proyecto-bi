-- =====================================================================
-- Data Warehouse - Esquema Estrella (Entregable 4)
-- Proyecto BI: Mercado Laboral Tech en Ecuador
-- Motor: PostgreSQL  |  Modelo: estrella pura (una tabla de hechos)
-- Fiel al diseno del Entregable 2.
-- Orden: primero las dimensiones, luego la tabla de hechos, luego la puente.
-- =====================================================================

-- Limpia las tablas si ya existian (para poder re-ejecutar este script).
DROP TABLE IF EXISTS puente_oferta_tecnologia CASCADE;
DROP TABLE IF EXISTS fact_ofertas_empleo CASCADE;
DROP TABLE IF EXISTS dim_tiempo CASCADE;
DROP TABLE IF EXISTS dim_modalidad CASCADE;
DROP TABLE IF EXISTS dim_fuente CASCADE;
DROP TABLE IF EXISTS dim_rol CASCADE;
DROP TABLE IF EXISTS dim_ubicacion CASCADE;
DROP TABLE IF EXISTS dim_tecnologia CASCADE;

-- ─────────────────────────────── DIMENSIONES ───────────────────────────────

CREATE TABLE dim_tiempo (
    id_tiempo                  SERIAL       PRIMARY KEY,
    fecha                      DATE         NOT NULL,
    dia                        SMALLINT,
    mes                        SMALLINT,
    nombre_mes                 VARCHAR(15),
    trimestre                  SMALLINT,
    semana                     SMALLINT,
    anio                       SMALLINT,
    salario_promedio_nacional  DECIMAL(10,2),   -- valor de referencia del INEC
    sector_referencia          VARCHAR(60)
);

CREATE TABLE dim_modalidad (
    id_modalidad      SERIAL       PRIMARY KEY,
    nombre_modalidad  VARCHAR(20)  NOT NULL     -- Remoto / Presencial / Hibrido / No especificado
);

CREATE TABLE dim_fuente (
    id_fuente      SERIAL       PRIMARY KEY,
    nombre_fuente  VARCHAR(40)  NOT NULL,
    tipo_fuente    VARCHAR(20),                 -- scraping / api / csv
    ambito         VARCHAR(20),                 -- local / internacional / nacional
    url            VARCHAR(120)
);

CREATE TABLE dim_rol (
    id_rol         SERIAL       PRIMARY KEY,
    nombre_rol     VARCHAR(50)  NOT NULL,       -- Desarrollador / Datos / QA / Otro
    categoria_rol  VARCHAR(30)
);

CREATE TABLE dim_ubicacion (
    id_ubicacion  SERIAL       PRIMARY KEY,
    ciudad        VARCHAR(50),
    provincia     VARCHAR(50),
    pais          VARCHAR(40)
);

CREATE TABLE dim_tecnologia (
    id_tecnologia    SERIAL       PRIMARY KEY,
    nombre_tecnologia VARCHAR(40) NOT NULL,
    tipo_tecnologia  VARCHAR(30)               -- lenguaje / framework / base_datos / herramienta / cloud
);

-- ─────────────────────────────── TABLA DE HECHOS ───────────────────────────

CREATE TABLE fact_ofertas_empleo (
    id_oferta         SERIAL        PRIMARY KEY,
    id_tiempo         INT           NOT NULL REFERENCES dim_tiempo(id_tiempo),
    id_fuente         INT           NOT NULL REFERENCES dim_fuente(id_fuente),
    id_rol            INT           NOT NULL REFERENCES dim_rol(id_rol),
    id_ubicacion      INT           NOT NULL REFERENCES dim_ubicacion(id_ubicacion),
    id_modalidad      INT           NOT NULL REFERENCES dim_modalidad(id_modalidad),
    salario_ofertado  DECIMAL(10,2),                    -- NULL si la fuente no lo publica
    tiene_salario     SMALLINT      CHECK (tiene_salario IN (0,1)),
    es_remota         SMALLINT      CHECK (es_remota IN (0,1)),
    num_tecnologias   INT           CHECK (num_tecnologias >= 0),
    conteo_oferta     INT           DEFAULT 1
);

-- ─────────────────────────────── TABLA PUENTE ──────────────────────────────
-- Resuelve la relacion muchos-a-muchos entre ofertas y tecnologias.

CREATE TABLE puente_oferta_tecnologia (
    id_oferta      INT  NOT NULL REFERENCES fact_ofertas_empleo(id_oferta),
    id_tecnologia  INT  NOT NULL REFERENCES dim_tecnologia(id_tecnologia),
    PRIMARY KEY (id_oferta, id_tecnologia)
);

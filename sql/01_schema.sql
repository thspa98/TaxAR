-- ============================================================
-- Schema: Transparencia Fiscal Argentina
-- Postgres / Supabase
-- ============================================================

-- ============================================
-- 1. JURISDICCIONES
-- ============================================
CREATE TABLE jurisdicciones (
    id              SERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    nivel           TEXT NOT NULL CHECK (nivel IN ('nacional','provincial','municipal')),
    jurisdiccion_padre_id INTEGER REFERENCES jurisdicciones(id),
    codigo_indec    TEXT,
    region_indec    TEXT,
    activa          BOOLEAN DEFAULT TRUE,
    creado_en       TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 2. PERIODOS
-- ============================================
CREATE TABLE periodos (
    id              SERIAL PRIMARY KEY,
    anio            INTEGER NOT NULL,
    mes             INTEGER CHECK (mes BETWEEN 1 AND 12),
    tipo            TEXT NOT NULL CHECK (tipo IN ('mensual','trimestral','anual')),
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE NOT NULL,
    UNIQUE (anio, mes, tipo)
);

-- ============================================
-- 3. FUENTES
-- ============================================
CREATE TABLE fuentes (
    id                      SERIAL PRIMARY KEY,
    jurisdiccion_id         INTEGER REFERENCES jurisdicciones(id),
    nombre                  TEXT NOT NULL,
    organismo               TEXT,
    url                     TEXT NOT NULL,
    tipo_archivo            TEXT,
    frecuencia_actualizacion TEXT,
    confiabilidad           TEXT DEFAULT 'oficial',
    ultima_revision         DATE,
    notas                   TEXT
);

-- ============================================
-- 4. CATEGORIAS (taxonomía estandarizada, jerárquica)
--    clasificacion distingue dos sistemas que NO son intercambiables:
--    - 'economica'  -> objeto del gasto (personal, transferencias, subsidios...)
--                      es como Nación publica su Base Caja mensual
--    - 'funcional'  -> finalidad y función (Salud, Educación, Seguridad...)
--                      es como las provincias suelen publicar ejecución
--    Para comparar Nación vs provincias en "Salud" hace falta la vista
--    funcional de Nación (Cuenta de Inversión), no la Base Caja mensual.
-- ============================================
CREATE TABLE categorias (
    id                  SERIAL PRIMARY KEY,
    nombre              TEXT NOT NULL,
    slug                TEXT UNIQUE NOT NULL,
    tipo                TEXT NOT NULL CHECK (tipo IN ('ingreso','gasto')),
    clasificacion       TEXT NOT NULL DEFAULT 'economica' CHECK (clasificacion IN ('economica','funcional')),
    categoria_padre_id  INTEGER REFERENCES categorias(id),
    nivel_jerarquia     INTEGER NOT NULL DEFAULT 1,
    orden_visualizacion INTEGER DEFAULT 0,
    clasificacion_cofog TEXT
);

-- ============================================
-- 5. HECHOS FISCALES (detalle)
--
--    TRES DIMENSIONES CRITICAS DE COMPARABILIDAD
--    (descubiertas al cruzar los datos reales de Córdoba con los de Nación;
--     sin ellas el sitio compara peras con manzanas y publica cifras erróneas):
--
--    a) universo -> QUÉ organismos entran en el número.
--       Córdoba publica "Administración General Centralizada" en sus PDFs,
--       pero el consolidado de MECON incluye además organismos
--       descentralizados y la Caja de Jubilaciones. El resultado financiero
--       2026 de Córdoba es 439.906 M en universo 'central' y apenas
--       12.996 M en universo 'apnf' — una diferencia de 34x, porque la
--       Caja de Jubilaciones tiene déficit de -418.575 M. Publicar uno
--       por el otro sería un error grave.
--
--    b) tipo_dato -> PRESUPUESTO (lo que se planea gastar, aprobado por ley)
--       vs EJECUTADO (lo que realmente se gastó, base caja).
--       La Base Caja mensual de Nación es EJECUTADO; los archivos de
--       presupuesto provincial son PRESUPUESTO. No son la misma cosa y
--       no deben graficarse en la misma serie sin aclararlo.
--
--    c) unidad_monto -> Nación y el consolidado MECON publican en MILLONES;
--       los PDFs de Córdoba publican en PESOS. Se normaliza todo a
--       millones en la ingesta, pero se deja registro de la unidad origen.
--
--    d) base_contable -> CAJA (se registra cuando el dinero entra/sale)
--       vs DEVENGADO (se registra cuando nace la obligación, aunque se
--       pague después). La Base Caja mensual de Nación es 'caja'; las
--       ejecuciones provinciales son 'devengado'. Un mismo gasto puede
--       aparecer en meses distintos según el criterio, así que sumar o
--       comparar ambos sin aclararlo produce cifras engañosas.
-- ============================================
CREATE TABLE hechos_fiscales (
    id                      BIGSERIAL PRIMARY KEY,
    jurisdiccion_id         INTEGER NOT NULL REFERENCES jurisdicciones(id),
    periodo_id              INTEGER NOT NULL REFERENCES periodos(id),
    categoria_id            INTEGER NOT NULL REFERENCES categorias(id),
    monto                   NUMERIC(20,2) NOT NULL,   -- SIEMPRE en millones de $ARS
    universo                TEXT NOT NULL DEFAULT 'central'
                            CHECK (universo IN ('central','apnf','consolidado')),
    tipo_dato               TEXT NOT NULL DEFAULT 'ejecutado'
                            CHECK (tipo_dato IN ('presupuesto','ejecutado')),
    base_contable           TEXT NOT NULL DEFAULT 'devengado'
                            CHECK (base_contable IN ('caja','devengado')),
    unidad_origen           TEXT NOT NULL DEFAULT 'millones'
                            CHECK (unidad_origen IN ('pesos','millones')),
    categoria_raw_original  TEXT,
    fuente_id               INTEGER NOT NULL REFERENCES fuentes(id),
    fecha_carga             TIMESTAMPTZ DEFAULT now(),
    UNIQUE (jurisdiccion_id, periodo_id, categoria_id, universo, tipo_dato, base_contable, fuente_id)
);
CREATE INDEX idx_hechos_jurisdiccion_periodo ON hechos_fiscales(jurisdiccion_id, periodo_id);
CREATE INDEX idx_hechos_categoria ON hechos_fiscales(categoria_id);
CREATE INDEX idx_hechos_universo_tipo ON hechos_fiscales(universo, tipo_dato, base_contable);

-- ============================================
-- 6. RESULTADOS FISCALES (KPIs headline)
--    Mismas dimensiones de comparabilidad que hechos_fiscales.
-- ============================================
CREATE TABLE resultados_fiscales (
    id                  BIGSERIAL PRIMARY KEY,
    jurisdiccion_id     INTEGER NOT NULL REFERENCES jurisdicciones(id),
    periodo_id          INTEGER NOT NULL REFERENCES periodos(id),
    universo            TEXT NOT NULL DEFAULT 'central'
                        CHECK (universo IN ('central','apnf','consolidado')),
    tipo_dato           TEXT NOT NULL DEFAULT 'ejecutado'
                        CHECK (tipo_dato IN ('presupuesto','ejecutado')),
    base_contable       TEXT NOT NULL DEFAULT 'devengado'
                        CHECK (base_contable IN ('caja','devengado')),
    ingresos_totales    NUMERIC(20,2),
    gastos_totales      NUMERIC(20,2),
    gastos_primarios    NUMERIC(20,2),
    resultado_economico NUMERIC(20,2),
    resultado_primario  NUMERIC(20,2),
    intereses_deuda     NUMERIC(20,2),
    resultado_financiero NUMERIC(20,2),
    fuente_id           INTEGER NOT NULL REFERENCES fuentes(id),
    UNIQUE (jurisdiccion_id, periodo_id, universo, tipo_dato, base_contable)
);

-- ============================================
-- 7. INDICADORES DE CONTEXTO
-- ============================================
-- tipo_indicador para población:
--   'poblacion_proyectada' -> proyección INDEC base Censo 2010 (cruda)
--   'poblacion_censo'      -> conteo real del Censo 2022
--   'poblacion'            -> serie AJUSTADA: proyección reescalada al censo.
--                             Es la que deben usar los cálculos per cápita.
-- Por qué: las proyecciones base 2010 se desvían fuerte del censo real 2022
-- (Santa Cruz -12,1%, Chaco -8,0%, Chubut -7,3%). Usar la proyección cruda
-- subestimaría el gasto per cápita de esas provincias en la misma magnitud
-- y falsearía los rankings del sitio. Se guardan las tres para que el
-- cálculo sea auditable.
CREATE TABLE indicadores_contexto (
    id              BIGSERIAL PRIMARY KEY,
    jurisdiccion_id INTEGER NOT NULL REFERENCES jurisdicciones(id),
    periodo_id      INTEGER NOT NULL REFERENCES periodos(id),
    tipo_indicador  TEXT NOT NULL CHECK (tipo_indicador IN
                        ('poblacion','poblacion_proyectada','poblacion_censo',
                         'pbg','pbi_nacional')),
    valor           NUMERIC(18,2) NOT NULL,
    fuente_id       INTEGER NOT NULL REFERENCES fuentes(id),
    UNIQUE (jurisdiccion_id, periodo_id, tipo_indicador)
);

-- ============================================
-- 8. COSTO DE VIDA
-- ============================================
CREATE TABLE indicadores_costo_vida (
    id              BIGSERIAL PRIMARY KEY,
    region_indec    TEXT NOT NULL,
    periodo_id      INTEGER NOT NULL REFERENCES periodos(id),
    indicador       TEXT NOT NULL CHECK (indicador IN ('ipc_general','canasta_basica_alimentaria','canasta_basica_total')),
    valor           NUMERIC(18,2) NOT NULL,
    variacion_mensual NUMERIC(6,2),
    variacion_interanual NUMERIC(6,2),
    fuente_id       INTEGER NOT NULL REFERENCES fuentes(id),
    UNIQUE (region_indec, periodo_id, indicador)
);

-- ============================================
-- VISTAS
-- ============================================
CREATE VIEW vw_series_resultado_fiscal AS
SELECT j.nombre AS jurisdiccion, j.slug, j.nivel, p.anio, p.mes, p.fecha_inicio,
       r.universo, r.tipo_dato, r.base_contable,
       r.ingresos_totales, r.gastos_totales, r.gastos_primarios,
       r.resultado_economico, r.resultado_primario,
       r.intereses_deuda, r.resultado_financiero
FROM resultados_fiscales r
JOIN jurisdicciones j ON j.id = r.jurisdiccion_id
JOIN periodos p ON p.id = r.periodo_id
ORDER BY j.nombre, p.fecha_inicio;

-- Ranking entre jurisdicciones comparables: fuerza mismo universo,
-- tipo_dato y base_contable, e incorpora población para el per cápita.
CREATE VIEW vw_ranking_jurisdicciones AS
SELECT p.anio, r.universo, r.tipo_dato, r.base_contable,
       j.nombre AS jurisdiccion, j.slug AS jurisdiccion_slug, j.nivel,
       r.ingresos_totales, r.gastos_totales, r.resultado_financiero,
       ic.valor AS poblacion,
       CASE WHEN ic.valor > 0
            THEN ROUND(r.gastos_totales * 1000000 / ic.valor, 2) END AS gasto_percapita_pesos,
       CASE WHEN r.ingresos_totales > 0
            THEN ROUND(r.resultado_financiero / r.ingresos_totales * 100, 2) END AS resultado_pct_ingresos
FROM resultados_fiscales r
JOIN jurisdicciones j ON j.id = r.jurisdiccion_id
JOIN periodos p ON p.id = r.periodo_id
LEFT JOIN indicadores_contexto ic
       ON ic.jurisdiccion_id = r.jurisdiccion_id
      AND ic.periodo_id = r.periodo_id
      AND ic.tipo_indicador = 'poblacion';

-- Serie deflactada a pesos constantes.
-- Con inflación argentina, una serie nominal de 21 años es ilegible: todo
-- "crece" enormemente aunque el gasto real caiga. Esta vista convierte a
-- pesos del año base usando el IPC regional de cada jurisdicción.
-- LIMITACIÓN: el IPC oficial de INDEC arranca en dic-2016, así que sólo
-- deflacta 2017 en adelante. Para 2005-2016 devuelve NULL en vez de un
-- número inventado (el IPC 2007-2015 además está cuestionado por la
-- intervención del INDEC en ese período).
CREATE VIEW vw_series_deflactada AS
WITH ipc_anual AS (
    SELECT p.anio, icv.region_indec, AVG(icv.valor) AS ipc_prom
    FROM indicadores_costo_vida icv
    JOIN periodos p ON p.id = icv.periodo_id
    WHERE icv.indicador = 'ipc_general'
    GROUP BY p.anio, icv.region_indec
),
base AS (
    SELECT region_indec, ipc_prom FROM ipc_anual
    WHERE anio = (SELECT MAX(anio) FROM ipc_anual)
)
SELECT j.nombre AS jurisdiccion, j.slug AS jurisdiccion_slug, p.anio,
       r.universo, r.tipo_dato, r.base_contable,
       r.gastos_totales AS gastos_nominales,
       CASE WHEN ia.ipc_prom IS NOT NULL AND ia.ipc_prom > 0
            THEN ROUND(r.gastos_totales * b.ipc_prom / ia.ipc_prom, 2) END AS gastos_constantes,
       (SELECT MAX(anio) FROM ipc_anual) AS anio_base
FROM resultados_fiscales r
JOIN jurisdicciones j ON j.id = r.jurisdiccion_id
JOIN periodos p ON p.id = r.periodo_id
LEFT JOIN ipc_anual ia ON ia.anio = p.anio AND ia.region_indec = j.region_indec
LEFT JOIN base b ON b.region_indec = j.region_indec;

-- Dependencia de la Nación: qué porcentaje de los recursos tributarios
-- de cada provincia viene de origen nacional (coparticipación) vs propio.
-- Es uno de los indicadores más políticamente relevantes del federalismo.
CREATE VIEW vw_dependencia_nacion AS
SELECT p.anio, j.nombre AS jurisdiccion, j.slug AS jurisdiccion_slug,
       h.universo, h.tipo_dato,
       SUM(CASE WHEN c.slug='ing-prov-impuestos-propios' THEN h.monto END) AS tributarios_propios,
       SUM(CASE WHEN c.slug='ing-prov-coparticipacion'  THEN h.monto END) AS tributarios_nacionales,
       ROUND(
         SUM(CASE WHEN c.slug='ing-prov-coparticipacion' THEN h.monto END) * 100.0
         / NULLIF(SUM(CASE WHEN c.slug IN ('ing-prov-impuestos-propios','ing-prov-coparticipacion')
                           THEN h.monto END), 0), 2) AS pct_dependencia_nacional
FROM hechos_fiscales h
JOIN jurisdicciones j ON j.id = h.jurisdiccion_id
JOIN categorias c ON c.id = h.categoria_id
JOIN periodos p ON p.id = h.periodo_id
WHERE j.nivel = 'provincial'
GROUP BY p.anio, j.nombre, j.slug, h.universo, h.tipo_dato;

CREATE VIEW vw_gasto_percapita AS
SELECT j.nombre AS jurisdiccion, c.nombre AS categoria, c.clasificacion, p.anio, p.mes,
       h.universo, h.tipo_dato,
       h.monto,
       ic.valor AS poblacion,
       ROUND(h.monto * 1000000 / NULLIF(ic.valor,0), 2) AS gasto_percapita_pesos
FROM hechos_fiscales h
JOIN jurisdicciones j ON j.id = h.jurisdiccion_id
JOIN categorias c ON c.id = h.categoria_id
JOIN periodos p ON p.id = h.periodo_id
LEFT JOIN indicadores_contexto ic
       ON ic.jurisdiccion_id = h.jurisdiccion_id
      AND ic.periodo_id = h.periodo_id
      AND ic.tipo_indicador = 'poblacion'
WHERE c.tipo = 'gasto';

-- Comparador entre jurisdicciones: SOLO devuelve filas del mismo universo
-- y mismo tipo_dato, para que sea imposible comparar sin querer un
-- presupuesto contra un ejecutado, o adm. central contra APNF.
CREATE VIEW vw_comparador_funcional AS
SELECT c.nombre AS categoria, c.slug AS categoria_slug,
       p.anio, h.universo, h.tipo_dato,
       j.nombre AS jurisdiccion, j.slug AS jurisdiccion_slug,
       h.monto
FROM hechos_fiscales h
JOIN jurisdicciones j ON j.id = h.jurisdiccion_id
JOIN categorias c ON c.id = h.categoria_id
JOIN periodos p ON p.id = h.periodo_id
WHERE c.clasificacion = 'funcional' AND c.tipo = 'gasto';

# Diseño de base de datos — Transparencia Fiscal Argentina
## Nación + 5 jurisdicciones provinciales (fase 1)

---

## 1. Qué jurisdicciones cubrir y por qué

Investigué las fuentes disponibles antes de diseñar el esquema, porque la elección de jurisdicciones depende de qué tan fácil es conseguir datos comparables.

**Hallazgo clave:** el Ministerio de Economía (Secretaría de Hacienda) publica un consolidado con la **ejecución presupuestaria de las 24 jurisdicciones** (23 provincias + CABA) en el mismo esquema estandarizado (Ahorro-Inversión-Financiamiento) y con la misma clasificación por finalidad y función. Esto es enorme para vos: significa que **no necesitás scrapear 5 portales provinciales distintos con 5 formatos distintos** — hay una fuente única y ya normalizada.

- [Ejecución Presupuestaria Provincial — MECON](https://www.argentina.gob.ar/economia/sechacienda/coordinacion-fiscal-provincial/ejecucion-presupuestaria-provincial)
- [Gastos por finalidad y función (las 24 jurisdicciones)](https://www.argentina.gob.ar/economia/sechacienda/coordinacion-fiscal-provincial/ejecucion-presupuestaria-provincial/gastos-por)
- [Presupuestos provinciales (descarga por jurisdicción)](https://www.argentina.gob.ar/economia/sechacienda/coordinacion-fiscal-provincial/ejecucion-presupuestaria-provincial/presupuestos)

Además, CIPPEC mantiene el **Índice de Transparencia Presupuestaria Provincial (ITPP)**, que mide qué tan buena es la información fiscal que publica cada provincia. En la edición 2024, el ranking lo lideran Córdoba (9,90/10), Entre Ríos (9,75) y Santa Fe (9,70).

- [ITPP 2024 — CIPPEC](https://www.cippec.org/publicacion/indice-de-transparencia-presupuestaria-provincial-edicion-2024/)

**Recomendación para las 5 jurisdicciones de la fase 1** (cruzando tamaño económico/poblacional con calidad de datos):

| Jurisdicción | Por qué | Fuente propia además de MECON |
|---|---|---|
| **CABA** | Mejor portal de datos abiertos del país: CSV/XLSX/JSON, actualización trimestral | [data.buenosaires.gob.ar](https://data.buenosaires.gob.ar/dataset/presupuesto-ejecutado) |
| **Buenos Aires (provincia)** | La más grande por población y presupuesto (~38% del gasto provincial consolidado) | [Provincia Abierta](https://www.gba.gob.ar/provinciaabierta) |
| **Córdoba** | #1 en el ranking de transparencia CIPPEC, 2da economía provincial | [Gestión Abierta Córdoba](https://datosgestionabierta.cba.gov.ar/dataset/presupuesto) |
| **Santa Fe** | #3 en transparencia CIPPEC, 3ra economía provincial | Portal propio + MECON |
| **Mendoza** | Portal de datos abiertos activo, 5ta economía provincial | [Datos Abiertos Mendoza](https://datosabiertos.mendoza.gov.ar/) |

Con esto cubrís Nación + 5 jurisdicciones que concentran una porción muy grande del gasto público subnacional total, y las que tienen mejor calidad de fuente — la combinación ideal para arrancar.

---

## 2. Arquitectura de datos: ¿una sola base?

Sí. Una única base de datos relacional (Postgres vía **Supabase**) con un modelo que separa:

1. **Quién** genera el dato (jurisdicción)
2. **Cuándo** (período)
3. **Qué categoría** de ingreso/gasto es, en una taxonomía **estandarizada** común a todas las jurisdicciones (para que sean comparables aunque cada provincia use nombres distintos)
4. **Cuánto** (el monto, el hecho fiscal en sí)
5. **De dónde salió** el dato (fuente, URL, fecha de carga) — esto es no negociable en un sitio de transparencia: cada número tiene que ser auditable

El desafío real de este tipo de proyecto no es la base de datos — es la **normalización de categorías**. Cada provincia clasifica el gasto con nombres propios. Por eso el esquema separa "categoría cruda" (como la publica la fuente) de "categoría canónica" (la que usás vos para comparar). Uso la clasificación por Finalidad y Función que ya es relativamente estándar en Argentina (Salud, Educación, Seguridad Social, Vivienda, Deuda Pública, etc.) porque MECON ya la usa para consolidar las 24 jurisdicciones.

---

## 3. Modelo de tablas

```
jurisdicciones ──┬── hechos_fiscales ──── categorias (jerárquica, autorreferencial)
                  │         │
                  │         └── fuentes
                  │
                  ├── resultados_fiscales (KPIs: ingresos/gastos/resultado por período)
                  │
                  ├── indicadores_contexto (población, PBG)
                  │
                  └── indicadores_costo_vida (IPC regional, canasta básica)

periodos ── (referenciado por hechos_fiscales, resultados_fiscales, indicadores_*)
```

### Tablas principales

**`jurisdicciones`** — Nación, provincias, (municipios a futuro)
**`periodos`** — meses/años, para series de tiempo
**`categorias`** — taxonomía estandarizada, jerárquica (ingreso/gasto → rubro → subrubro)
**`fuentes`** — de dónde viene cada dato, con URL y fecha de actualización (trazabilidad)
**`hechos_fiscales`** — la tabla central: un monto, en una categoría, para una jurisdicción y período
**`resultados_fiscales`** — los KPIs headline por jurisdicción/período (ingresos totales, gastos primarios, resultado primario, intereses, resultado financiero) — separada de `hechos_fiscales` para que los gráficos principales no dependan de sumar decenas de filas cada vez
**`indicadores_contexto`** — población y PBG por jurisdicción/año, necesario para calcular per cápita y rankings justos (no tiene sentido comparar el gasto total de Buenos Aires con el de Mendoza sin dividir por habitantes)
**`indicadores_costo_vida`** — IPC regional e INDEC (GBA, Pampeana, Cuyo, etc.) y canasta básica, para la sección "cuánto cuesta vivir"

---

## 4. Script SQL (Postgres / Supabase)

```sql
-- ============================================
-- 1. JURISDICCIONES
-- ============================================
CREATE TABLE jurisdicciones (
    id              SERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL,               -- "Nación", "Córdoba", "CABA"
    slug            TEXT UNIQUE NOT NULL,         -- "nacion", "cordoba", "caba"
    nivel           TEXT NOT NULL CHECK (nivel IN ('nacional','provincial','municipal')),
    jurisdiccion_padre_id INTEGER REFERENCES jurisdicciones(id), -- provincia de un municipio (futuro)
    codigo_indec    TEXT,                         -- código oficial INDEC, para cruzar con otras fuentes
    region_indec    TEXT,                         -- GBA/Pampeana/NOA/NEA/Cuyo/Patagonia (para IPC regional)
    activa          BOOLEAN DEFAULT TRUE,         -- fase 1 = true solo para las 6 jurisdicciones cubiertas
    creado_en       TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 2. PERIODOS
-- ============================================
CREATE TABLE periodos (
    id              SERIAL PRIMARY KEY,
    anio            INTEGER NOT NULL,
    mes             INTEGER CHECK (mes BETWEEN 1 AND 12), -- NULL si es un período anual
    tipo            TEXT NOT NULL CHECK (tipo IN ('mensual','trimestral','anual')),
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE NOT NULL,
    UNIQUE (anio, mes, tipo)
);

-- ============================================
-- 3. FUENTES (trazabilidad — clave para un sitio de transparencia)
-- ============================================
CREATE TABLE fuentes (
    id                      SERIAL PRIMARY KEY,
    jurisdiccion_id         INTEGER REFERENCES jurisdicciones(id),
    nombre                  TEXT NOT NULL,           -- "MECON - Base Caja Mensual"
    organismo               TEXT,                    -- "Secretaría de Hacienda"
    url                     TEXT NOT NULL,
    tipo_archivo            TEXT,                    -- "xlsx", "csv", "api"
    frecuencia_actualizacion TEXT,                    -- "mensual", "trimestral"
    confiabilidad           TEXT DEFAULT 'oficial',   -- "oficial", "estimado", "prensa"
    ultima_revision         DATE,
    notas                   TEXT
);

-- ============================================
-- 4. CATEGORIAS (taxonomía estandarizada, jerárquica)
-- ============================================
CREATE TABLE categorias (
    id                  SERIAL PRIMARY KEY,
    nombre              TEXT NOT NULL,               -- "Salud", "Jubilaciones", "Educación"
    slug                TEXT UNIQUE NOT NULL,
    tipo                TEXT NOT NULL CHECK (tipo IN ('ingreso','gasto')),
    categoria_padre_id  INTEGER REFERENCES categorias(id), -- jerarquía: rubro > subrubro > detalle
    nivel_jerarquia     INTEGER NOT NULL DEFAULT 1,  -- 1 = rubro grande, 2 = subrubro, 3 = detalle
    orden_visualizacion INTEGER DEFAULT 0,
    clasificacion_cofog TEXT                         -- código de Finalidad y Función si aplica
);

-- ============================================
-- 5. HECHOS FISCALES (tabla central de detalle)
-- ============================================
CREATE TABLE hechos_fiscales (
    id                      BIGSERIAL PRIMARY KEY,
    jurisdiccion_id         INTEGER NOT NULL REFERENCES jurisdicciones(id),
    periodo_id              INTEGER NOT NULL REFERENCES periodos(id),
    categoria_id            INTEGER NOT NULL REFERENCES categorias(id),
    monto                   NUMERIC(18,2) NOT NULL,     -- en $ARS
    categoria_raw_original  TEXT,                       -- nombre tal como lo publicó la fuente (auditoría)
    fuente_id               INTEGER NOT NULL REFERENCES fuentes(id),
    fecha_carga             TIMESTAMPTZ DEFAULT now(),
    UNIQUE (jurisdiccion_id, periodo_id, categoria_id, fuente_id)
);
CREATE INDEX idx_hechos_jurisdiccion_periodo ON hechos_fiscales(jurisdiccion_id, periodo_id);
CREATE INDEX idx_hechos_categoria ON hechos_fiscales(categoria_id);

-- ============================================
-- 6. RESULTADOS FISCALES (KPIs headline, para carga rápida de gráficos principales)
-- ============================================
CREATE TABLE resultados_fiscales (
    id                  BIGSERIAL PRIMARY KEY,
    jurisdiccion_id     INTEGER NOT NULL REFERENCES jurisdicciones(id),
    periodo_id          INTEGER NOT NULL REFERENCES periodos(id),
    ingresos_totales    NUMERIC(18,2),
    gastos_primarios    NUMERIC(18,2),
    resultado_primario  NUMERIC(18,2),
    intereses_deuda     NUMERIC(18,2),
    resultado_financiero NUMERIC(18,2),
    fuente_id           INTEGER NOT NULL REFERENCES fuentes(id),
    UNIQUE (jurisdiccion_id, periodo_id)
);

-- ============================================
-- 7. INDICADORES DE CONTEXTO (población, PBG — para per cápita y % PBI)
-- ============================================
CREATE TABLE indicadores_contexto (
    id              BIGSERIAL PRIMARY KEY,
    jurisdiccion_id INTEGER NOT NULL REFERENCES jurisdicciones(id),
    periodo_id      INTEGER NOT NULL REFERENCES periodos(id),
    tipo_indicador  TEXT NOT NULL CHECK (tipo_indicador IN ('poblacion','pbg','pbi_nacional')),
    valor           NUMERIC(18,2) NOT NULL,
    fuente_id       INTEGER NOT NULL REFERENCES fuentes(id),
    UNIQUE (jurisdiccion_id, periodo_id, tipo_indicador)
);

-- ============================================
-- 8. COSTO DE VIDA (IPC regional INDEC, canasta básica)
-- ============================================
CREATE TABLE indicadores_costo_vida (
    id              BIGSERIAL PRIMARY KEY,
    region_indec    TEXT NOT NULL,              -- "GBA","Pampeana","NOA","NEA","Cuyo","Patagonia","Nacional"
    periodo_id      INTEGER NOT NULL REFERENCES periodos(id),
    indicador       TEXT NOT NULL CHECK (indicador IN ('ipc_general','canasta_basica_alimentaria','canasta_basica_total')),
    valor           NUMERIC(18,2) NOT NULL,
    variacion_mensual NUMERIC(6,2),
    variacion_interanual NUMERIC(6,2),
    fuente_id       INTEGER NOT NULL REFERENCES fuentes(id),
    UNIQUE (region_indec, periodo_id, indicador)
);

-- ============================================
-- VISTAS PARA LA WEB (consumo directo desde el frontend)
-- ============================================

-- Serie de tiempo lista para graficar (resultado fiscal por jurisdicción)
CREATE VIEW vw_series_resultado_fiscal AS
SELECT j.nombre AS jurisdiccion, j.slug, p.anio, p.mes, p.fecha_inicio,
       r.ingresos_totales, r.gastos_primarios, r.resultado_primario,
       r.intereses_deuda, r.resultado_financiero
FROM resultados_fiscales r
JOIN jurisdicciones j ON j.id = r.jurisdiccion_id
JOIN periodos p ON p.id = r.periodo_id
ORDER BY j.nombre, p.fecha_inicio;

-- Gasto per cápita por categoría (para "tops" y comparaciones)
CREATE VIEW vw_gasto_percapita AS
SELECT j.nombre AS jurisdiccion, c.nombre AS categoria, p.anio, p.mes,
       h.monto,
       ic.valor AS poblacion,
       ROUND(h.monto / NULLIF(ic.valor,0), 2) AS gasto_percapita
FROM hechos_fiscales h
JOIN jurisdicciones j ON j.id = h.jurisdiccion_id
JOIN categorias c ON c.id = h.categoria_id
JOIN periodos p ON p.id = h.periodo_id
LEFT JOIN indicadores_contexto ic
       ON ic.jurisdiccion_id = h.jurisdiccion_id
      AND ic.periodo_id = h.periodo_id
      AND ic.tipo_indicador = 'poblacion'
WHERE c.tipo = 'gasto';
```

---

## 5. Qué datos específicos mostrar (fase 1)

Para no dispersarte, arrancaría con un set acotado de categorías canónicas por el lado del gasto (las que más le importan al ciudadano común) y otro por ingresos:

**Gasto (categorías canónicas prioritarias):**
Salud, Educación, Seguridad Social (jubilaciones/pensiones), Seguridad (policía), Subsidios económicos (energía/transporte), Salarios de la administración pública, Deuda pública (intereses), Obra pública/infraestructura.

**Ingreso (categorías canónicas prioritarias):**
Impuestos propios vs. Coparticipación federal (esto es políticamente clave a nivel provincial — cuánto depende cada provincia de la Nación), Ingresos no tributarios, Endeudamiento.

**KPIs headline por jurisdicción/período:** ingresos totales, gastos primarios, resultado primario, intereses, resultado financiero — igual que el gráfico que ya transcribiste para Nación.

---

## 6. Cómo estas tablas alimentan cada feature interactiva

| Feature | Cómo se arma con el esquema |
|---|---|
| **Tops / rankings** | `vw_gasto_percapita` ordenado por `gasto_percapita DESC`, filtrando por categoría y período. Ej: "top 5 provincias que más gastan en salud por habitante" |
| **Gráficos de series de tiempo** | `vw_series_resultado_fiscal` filtrado por `jurisdiccion_id`, graficado directo en Chart.js/Recharts |
| **Comparador entre jurisdicciones** | Query que pivotea `hechos_fiscales` por `categoria_id` con `jurisdiccion_id` en columnas, mismo `periodo_id` — "Córdoba vs. Santa Fe, gasto en educación, 2026" |
| **"Cuánto cuesta vivir"** | Cruza `indicadores_costo_vida` (canasta básica por región) con salario mínimo o con el gasto en AUH/jubilación mínima de `hechos_fiscales` — ej. "cuántas canastas básicas cubre la jubilación mínima" |
| **% del gasto total** | Cálculo directo: `monto categoría / gastos_primarios del período` desde `resultados_fiscales` |

---

## 7. Proceso de actualización (resumen operativo)

1. **Nación:** MECON publica el Excel de Base Caja ~día 15-20 del mes siguiente. Script mensual descarga, parsea y hace `UPSERT` en `hechos_fiscales` + `resultados_fiscales`.
2. **Las 5 provincias:** usar primero el consolidado de MECON (`gastos-por-finalidad-y-funcion`) porque ya viene comparable entre las 24 jurisdicciones — reduce el trabajo de mapeo de categorías a uno solo, no a cinco. Completar con los portales propios (CABA, Córdoba) cuando se necesite mayor frecuencia o detalle.
3. Cada carga registra su `fuente_id` con URL y fecha — así cualquier visitante de la web puede verificar de dónde salió cada número (clave para credibilidad en un sitio de transparencia).
4. Automatización recomendada: GitHub Actions corriendo un script Python mensualmente (gratis, sin necesidad de servidor propio).

---

## 8. Próximos pasos sugeridos

1. Cargar la tabla `categorias` con la taxonomía canónica definitiva (puedo ayudarte a armarla completa a partir de la clasificación por Finalidad y Función de MECON).
2. Escribir el script de ingesta para Nación (ya tenemos los datos de mayo 2026 transcriptos — sirve de caso de prueba).
3. Descargar el consolidado de las 24 jurisdicciones desde el link de "Gastos por finalidad y función" y cargar las 5 provincias elegidas.
4. Diseñar 2-3 vistas/queries concretas para el primer feature interactivo que quieras lanzar (sugiero empezar por "tops per cápita" porque es el más simple y más viral).

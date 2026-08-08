# TaxAR — Documento de traspaso

Para retomar el proyecto en otro chat sin perder contexto.

---

## Qué es el proyecto

Sitio de transparencia fiscal de Argentina para **público general**, con datos de
Nación, provincias y (a futuro) municipios. Objetivo: democratizar el conocimiento
sobre en qué se gasta el dinero de los impuestos. Features previstas: tops,
rankings, gráficos, comparadores entre jurisdicciones y "cuánto cuesta vivir".

---

## Estado actual: base de datos lista y verificada

**Cargado: 25 jurisdicciones × 21 años (2005–2025) + Nación + población (24 × 31 años)
+ IPC (6 regiones × 115 meses). Todos los controles en verde.**

Probado end-to-end contra Postgres 16 real (no solo sintaxis).

**Los dos bloqueantes anteriores están resueltos:** ya funcionan los rankings
per cápita y la serie deflactada a pesos constantes.

### Archivos del proyecto

| Archivo | Qué es |
|---|---|
| `01_schema.sql` | Esquema completo: 8 tablas + 7 vistas. Postgres/Supabase. |
| `02_taxonomia_seed.sql` | Taxonomía canónica (~45 categorías, económica + funcional). |
| `ingesta_serie_aif.py` | **El principal.** Carga las 24 jurisdicciones × 21 años. |
| `ingesta_indec.py` | Población (con ajuste censal) + IPC por región. |
| `ingesta_nacion.py` | Base Caja mensual de Nación. |
| `ingesta_cordoba.py` | Presupuesto Córdoba 2010-2026 + gasto funcional. |
| `mayo_2026_nacion.csv` | Caso de prueba de Nación. |
| `estado_base_datos.md` | Detalle de verificaciones y datos disponibles. |
| `hallazgos_cruce_cordoba.md` | Problemas de comparabilidad detectados. |
| `diseno_base_datos_transparencia_fiscal.md` | Diseño y fuentes provinciales. |

### Orden de ejecución

```bash
psql $DATABASE_URL -f 01_schema.sql
psql $DATABASE_URL -f 02_taxonomia_seed.sql
python ingesta_serie_aif.py --xlsx serie_aif-apnf-2025.xlsx
python ingesta_indec.py --poblacion c1_proyecciones_prov_2010_2040.xls \
  --censo c2022_tp_c_resumen.xlsx --ipc sh_ipc_aperturas.xls
python ingesta_nacion.py --csv mayo_2026_nacion.csv --anio 2026 --mes 5 \
  --ingresos-totales 14531657 --gastos-primarios 12607290 \
  --resultado-primario 1924367 --intereses 1445754 \
  --resultado-financiero 478613 --fuente-url "https://..."
python ingesta_cordoba.py --xls presupuesto_provincial_-_cordoba_1.xls \
  --pdf-funcional 04.0-Erogaciones....pdf --anio 2026 --serie-historica
```

---

## Las 4 dimensiones de comparabilidad (LO MÁS IMPORTANTE)

Sin esto el sitio publica cifras incorrectas. Todo dato lleva estos 4 campos
obligatorios y las vistas nunca los mezclan:

1. **`universo`** — `central` / `apnf` / `consolidado`
   Córdoba 2026: resultado financiero es **439.906 M** en universo central pero
   **12.996 M** en APNF (la Caja de Jubilaciones tiene déficit de -418.575 M).
   34x de diferencia.

2. **`tipo_dato`** — `presupuesto` (lo que se planea) / `ejecutado` (lo que se gastó)

3. **`base_contable`** — `caja` (cuando entra/sale la plata) / `devengado` (cuando
   nace la obligación). Nación Base Caja es `caja`; todas las provincias, `devengado`.

4. **`unidad_origen`** — `pesos` / `millones`. Todo se normaliza a millones al cargar.

---

## Población: el ajuste censal (leer antes de usar per cápita)

Las proyecciones de INDEC base Censo 2010 se desvían del censo real 2022:

| Jurisdicción | Desvío | Efecto en el per cápita si se usa la proyección cruda |
|---|---|---|
| Santa Cruz | −12,1% | subestima 13,8% |
| Chaco | −8,0% | subestima 8,7% |
| Chubut | −7,3% | subestima 7,9% |
| Corrientes | +6,4% | sobreestima 6,0% |

Se aplica un factor por jurisdicción (`censo2022 / proyección2022`) que reescala
toda la serie: conserva la forma del crecimiento y ancla el nivel al dato observado.
Es el ajuste intercensal estándar.

La tabla guarda **tres series** para que sea auditable:

- `poblacion_proyectada` — cruda, como la publica INDEC
- `poblacion_censo` — conteo real 2022
- `poblacion` — **ajustada; es la que usan los cálculos per cápita**

Cobertura: 24 jurisdicciones × 31 años (2010–2040). La serie fiscal arranca en
2005, así que 2005–2009 queda sin población.

---

## IPC y la serie deflactada

IPC oficial de INDEC: 6 regiones × 115 meses, **dic-2016 a jun-2026**.

**Limitación importante:** no cubre 2005–2016. De las 524 series fiscales,
239 son deflactables y 285 no. La vista devuelve `NULL` en vez de inventar
un número. Además, el IPC 2007–2015 está cuestionado por la intervención
del INDEC en ese período, así que completarlo requiere decidir qué fuente
alternativa usar (IPC de San Luis o CABA, o series privadas reconstruidas).

**Por qué importa deflactar — caso Buenos Aires:**

| Año | Gasto nominal (M$) | Gasto constante (M$) |
|---|---|---|
| 2017 | 550.681 | 54.293.563 |
| 2021 | 2.202.490 | 51.261.675 |
| 2024 | 25.382.641 | 45.139.733 |
| 2025 | 36.572.407 | 45.530.374 |

En términos nominales el gasto se multiplicó por 66. En pesos constantes
**cayó 16%**. Publicar la serie nominal sin aclarar daría exactamente la
impresión opuesta a la realidad.

---

## Vistas SQL listas para el frontend

- `vw_series_resultado_fiscal` — series de tiempo por jurisdicción
- `vw_ranking_jurisdicciones` — tops, **per cápita**, resultado como % de ingresos
- `vw_series_deflactada` — pesos constantes (2017+; NULL antes)
- `vw_dependencia_nacion` — % de recursos que vienen de coparticipación
- `vw_comparador_funcional` — Salud/Educación (solo Córdoba por ahora)
- `vw_gasto_percapita` — gasto por habitante por categoría

---

## Encaje con el modelo de página (TaxAR.html / TaxAR_1.html)

El modelo es un SPA React + Recharts, con `DATA` hardcodeado de Córdoba 2023
y 4 pestañas: Presupuesto, Impuestos, Salarios, Calculadora. El mapa marca
"22 provincias + CABA – datos en construcción".

| Campo del modelo | Vista/dato en la base | Estado |
|---|---|---|
| `budget.hist` (t/e por año) | `vw_series_resultado_fiscal` filtrando `tipo_dato` | **Listo**, 2010–2026 |
| `tax.own` / `tax.copart` | `vw_dependencia_nacion` | **Listo**, 24 prov × 21 años |
| `sal.total`, `sal.pct` | `gas-remuneraciones` / `gastos_totales` | **Listo**, 24 prov × 21 años |
| `budget.fn` (por función) | `vw_comparador_funcional` | **Parcial**: solo Córdoba |
| `tax.items` (IIBB, Inmob., Automotor, Sellos) | — | **Falta** (ver abajo) |

**Para que "no parezca tan IA":** los tres delatores del modelo son los emojis en
las pestañas, los datos redondos inventados (1.850.000 / 499.500) y la ausencia de
citas. Los últimos dos se resuelven solos al conectar datos reales: los números
verdaderos son irregulares (7.596.554 M) y cada uno trae su `fuente_id` con URL
verificable — que además es lo que le da credibilidad a un sitio de transparencia.

---

## Datos disponibles hoy para mostrar

### Ranking gasto total 2024 (provincias, APNF devengado)

| # | Jurisdicción | Gasto total (M $) | Resultado financiero (M $) |
|---|---|---|---|
| 1 | Buenos Aires | 25.382.641 | −1.383.357 |
| 2 | CABA | 9.228.575 | +295.540 |
| 3 | Córdoba | 7.596.554 | +381.199 |
| 4 | Santa Fe | 7.031.231 | +118.152 |
| 5 | Neuquén | 4.355.013 | +357.282 |

### Dependencia de la Nación 2024 — el dato más potente

| Más dependientes | % | Menos dependientes | % |
|---|---|---|---|
| Formosa | 93,3% | CABA | 11,8% |
| Santiago del Estero | 90,9% | Neuquén | 38,1% |
| La Rioja | 89,2% | Buenos Aires | 49,1% |

Formosa depende de la Nación 8 veces más que CABA. Disponible para los 21 años.

### Gasto per cápita 2024 — el ranking que estaba bloqueado

| # | Jurisdicción | Gasto (M$) | Población | $/habitante |
|---|---|---|---|---|
| 1 | Neuquén | 4.355.013 | 727.633 | 5.985.179 |
| 2 | Tierra del Fuego | 1.016.297 | 194.528 | 5.224.436 |
| 3 | Santa Cruz | 1.585.184 | 353.179 | 4.488.336 |
| 4 | La Pampa | 1.449.774 | 367.545 | 3.944.478 |
| … | | | | |
| 22 | Mendoza | 3.060.620 | 2.082.130 | 1.469.947 |
| 23 | Buenos Aires | 25.382.641 | 17.842.707 | 1.422.578 |
| 24 | Tucumán | 2.462.698 | 1.770.331 | 1.391.095 |

**Neuquén gasta 4,3x por habitante que Tucumán.** El ranking se invierte
respecto del gasto absoluto: Buenos Aires es 1° en total y 23° per cápita.
Las provincias patagónicas encabezan (regalías + poca población).

### Gasto funcional Córdoba 2026 (presupuesto, Adm. Central)

Educación y Cultura 3.500.314 M · Salud 1.208.065 M · Seguridad Interior 1.232.265 M.
Córdoba presupuesta casi 3x más en Educación que en Salud.

---

## Pendientes, por prioridad

### 1. IPC anterior a 2017 (opcional pero valioso)
La serie oficial arranca en dic-2016. Para deflactar 2005-2016 hay que elegir
una fuente alternativa y documentar la decisión: IPC de San Luis o CABA (que
cubrieron el período de intervención del INDEC), o series privadas
reconstruidas. Es una decisión metodológica que conviene explicitar en el sitio.

### 2. Población 2005-2009
Las proyecciones arrancan en 2010; la serie fiscal en 2005. Se puede extrapolar
hacia atrás o simplemente mostrar per cápita desde 2010.

### 3. Gasto funcional del resto de provincias
Hoy solo Córdoba. Buenos Aires ya está en `04 - Consolidadas.pdf` sin procesar.

### 4. Detalle de impuestos provinciales (IIBB, Inmobiliario, Automotor, Sellos)
La serie AIF solo trae "De Origen Provincial" agregado. El desglose por impuesto
requiere fuentes provinciales. Lo tenemos para Mendoza en `serie_mensual_26.pdf`.

### 5. Gasto funcional de Nación
Para comparar Salud/Educación entre niveles de gobierno hace falta Cuenta de
Inversión o Presupuesto Abierto — la Base Caja mensual es clasificación económica
y no tiene línea "Salud".

---

## Fuentes principales

| Fuente | Cobertura | Frecuencia |
|---|---|---|
| `serie_aif-apnf-2025.xlsx` (DNCFP-MECON) | 24 jurisdicciones, 2005-2025, ejecutado | Anual |
| Base Caja MECON | Nación, mensual | ~día 15-20 del mes siguiente |
| Presupuestos provinciales MECON | 24 jurisdicciones, presupuesto | Anual |
| `c1_proyecciones_prov_2010_2040.xls` (INDEC) | Población 24 jur., 2010-2040 | Esporádica |
| `c2022_tp_c_resumen.xlsx` (INDEC) | Censo 2022 real | Decenal |
| `sh_ipc_aperturas.xls` (INDEC) | IPC 6 regiones, dic-2016+ | Mensual |
| Portales provinciales | Detalle funcional y mensual | Variable |

URLs de INDEC:
- `https://www.indec.gob.ar/ftp/cuadros/poblacion/c1_proyecciones_prov_2010_2040.xls`
- `https://www.indec.gob.ar/ftp/cuadros/poblacion/c2022_tp_c_resumen.xlsx`
- `https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_aperturas.xls`

**Clave:** MECON publica el consolidado de las 24 jurisdicciones en formato
estandarizado. No hace falta scrapear 24 portales para los datos comparativos.

---

## Problemas de calidad detectados en fuentes oficiales

El pipeline los detecta automáticamente. Ya aparecieron tres:

1. **Córdoba 2021** en el `.xls` de presupuestos: la hoja es copia exacta de 2020
   (220 celdas idénticas, 0 distintas) y el nº de ley está vacío. Se omite.
2. **La Pampa 2025** en la serie AIF: todos los valores en cero (no reportó).
   Cargarlo como cero la haría aparecer como la provincia que menos gasta del país.
3. **Typo de INDEC**: en `c1_proyecciones_prov_2010_2040.xls` la hoja de Santa Fe
   se llama **"82-SANTE FE"**. Sin el alias, Santa Fe (3ª economía provincial)
   quedaba sin población y desaparecía de todos los rankings per cápita —
   sin ningún error visible. Se agregó un control de cobertura que verifica que
   toda jurisdicción provincial de la base tenga población cargada.

Conviene mantener estos controles al agregar fuentes nuevas.

---

## Lección de método

Los bugs más importantes los encontró la **verificación automática**, no la
revisión a ojo:

- El control de suma del PDF de Córdoba detectó que la extracción tomaba el
  subtotal del bloque de páginas equivocado (0,55% de error).
- El control de duplicados detectó la hoja 2021 repetida.
- El control de ceros detectó La Pampa.
- El control de cobertura detectó que Santa Fe faltaba por el typo "SANTE FE".

Cada adaptador nuevo debería traer su propia verificación contra un total
publicado por la fuente, y un control de cobertura que confirme que no
falta ninguna jurisdicción esperada.

# Estado de la base de datos — Transparencia Fiscal Argentina

**Cargado y verificado: 25 jurisdicciones × 21 años (2005–2025) + Nación.
8.908 hechos fiscales, 525 series de resultados. Todos los controles en verde.**

---

## El archivo que resuelve la fragmentación

`serie_aif-apnf-2025.xlsx` (DNCFP – MECON) es el hallazgo central. Contiene:

- **25 hojas**: Consolidado + 24 jurisdicciones (23 provincias + CABA)
- **21 años**: 2005 a 2025
- **Ejecución presupuestaria** (no presupuesto): lo que realmente se gastó
- **Mismo esquema AIF** en todas las hojas, mismo universo (APNF), en millones de pesos

Esto significa que **no necesitás pelearte con el sitio fragmentado de Buenos Aires** ni con los 24 portales provinciales para los datos comparativos del núcleo del sitio. Una sola fuente, ya normalizada por la Dirección Nacional de Coordinación Fiscal con las Provincias.

Los portales provinciales siguen siendo útiles, pero para el **detalle** (gasto funcional, series mensuales), no para la comparación básica.

---

## De dónde salió cada archivo que subiste

Los metadatos internos identificaron el origen de los que no lo decían:

| Archivo | Jurisdicción | Contenido | Uso |
|---|---|---|---|
| `serie_aif-apnf-2025.xlsx` | **Las 24 + Consolidado** | Ejecución AIF 2005-2025 | **Núcleo del sitio** — cargado |
| `presupuesto_provincial_-_cordoba_1.xls` | Córdoba | Presupuesto 2010-2026 | Serie de presupuesto |
| `04.0-Erogaciones...pdf` | Córdoba | Gasto funcional 2026 | Salud/Educación |
| `14-Cuenta-Ahorro...pdf` | Córdoba | AIF 2026 Adm. Central | Reconciliación |
| `04 - Consolidadas.pdf` | **Buenos Aires** | Presupuesto 2026 por finalidad | Gasto funcional BA |
| `serie_mensual_26.pdf` | **Mendoza** | Ejecución mensual 2026 | Serie alta frecuencia |
| `Esquema-4°-TRIM-2025.pdf` | **Mendoza** | Ejecución mensual 2025 | Serie alta frecuencia |
| `LRF Pres Aprob 2025.pdf` | **Santa Fe** | Presupuesto aprobado 2025 | Presupuesto SF |

Los dos "serie mensual" no decían la provincia en el texto; el metadato del PDF (`AIF Serie_mensual_25 Mza.xlsx`) reveló que son de Mendoza.

---

## Verificaciones que corrí (contra Postgres real)

| Control | Resultado |
|---|---|
| Suma de las 24 jurisdicciones = hoja Consolidado | **0,000% de diferencia en los 21 años** |
| Identidad contable: Ingresos − Gastos = Resultado financiero | **0 filas incumplen** (de 525) |
| Intereses derivados nunca negativos | **0 casos imposibles** |
| Verificación independiente de 3 valores contra el archivo fuente | **Coinciden exactamente** |

Que la suma de las 24 provincias reproduzca el Consolidado con cero diferencia en 21 años es la señal más fuerte de que el mapeo de categorías y la lectura de filas están bien.

---

## Cuarta dimensión de comparabilidad: base contable

Se agregó `base_contable` al esquema, además de `universo`, `tipo_dato` y `unidad_origen`:

- **Caja**: se registra cuando el dinero entra o sale. Es la Base Caja mensual de Nación.
- **Devengado**: se registra cuando nace la obligación, aunque se pague después. Son todas las ejecuciones provinciales.

Un mismo gasto puede caer en meses distintos según el criterio. Sumar o comparar ambos sin aclararlo produce cifras engañosas, así que el campo es obligatorio y las vistas del sitio no los mezclan.

Estado actual: 524 filas devengado (provincias) + 1 caja (Nación mayo 2026).

---

## Dato de calidad detectado: La Pampa 2025

La hoja de La Pampa tiene **todos los valores en cero para 2025** — la provincia no reportó. Un cero real y un "sin dato" no son lo mismo: cargarlo como cero hundiría los promedios y rankings del sitio (aparecería como la provincia que menos gasta del país).

El script lo detecta automáticamente y omite el año. La Pampa quedó con 20 años en vez de 21. El control corre solo para futuras cargas.

Sumado al caso de Córdoba 2021 (hoja duplicada de 2020), ya son **dos problemas de calidad en los archivos oficiales** que el pipeline detecta sin intervención manual.

---

## Lo que ya podés mostrar en el sitio

### Ranking de gasto total 2024 (provincias, APNF devengado)

| # | Jurisdicción | Gasto total (M $) | Resultado financiero (M $) |
|---|---|---|---|
| 1 | Buenos Aires | 25.382.641 | **−1.383.357** |
| 2 | CABA | 9.228.575 | +295.540 |
| 3 | Córdoba | 7.596.554 | +381.199 |
| 4 | Santa Fe | 7.031.231 | +118.152 |
| 5 | Neuquén | 4.355.013 | +357.282 |
| 6 | Entre Ríos | 3.282.784 | −34.792 |
| 7 | Mendoza | 3.060.620 | +141.578 |
| 8 | Chaco | 2.991.902 | −214.822 |
| 9 | Misiones | 2.631.059 | +4.467 |
| 10 | Tucumán | 2.462.698 | +253.543 |

### Dependencia de la Nación 2024 — el dato más potente para el público

Qué porcentaje de los recursos tributarios de cada provincia viene de coparticipación nacional en vez de impuestos propios:

**Más dependientes:**

| Jurisdicción | % de origen nacional |
|---|---|
| Formosa | **93,3%** |
| Santiago del Estero | 90,9% |
| La Rioja | 89,2% |
| Chaco | 87,3% |
| Catamarca | 87,1% |

**Menos dependientes:**

| Jurisdicción | % de origen nacional |
|---|---|
| CABA | **11,8%** |
| Neuquén | 38,1% |
| Buenos Aires | 49,1% |
| Chubut | 61,9% |
| Mendoza | 62,8% |

Formosa depende de la Nación **8 veces más** que CABA. Este contraste es exactamente el tipo de dato que explica el federalismo fiscal argentino a alguien sin formación económica, y ya está disponible para los 21 años.

---

## Vistas SQL listas para el frontend

- `vw_series_resultado_fiscal` — series de tiempo por jurisdicción
- `vw_ranking_jurisdicciones` — tops y rankings, con per cápita y resultado como % de ingresos
- `vw_dependencia_nacion` — el indicador de federalismo de arriba
- `vw_comparador_funcional` — comparación Salud/Educación (solo Córdoba por ahora)
- `vw_gasto_percapita` — gasto por habitante por categoría

---

## Lo que falta para desbloquear el resto

1. **Población por jurisdicción y año** (INDEC). Sin esto los rankings per cápita no funcionan — y comparar el gasto de Buenos Aires con el de Formosa sin dividir por habitantes no dice nada. Es el bloqueante más importante ahora.
2. **Gasto funcional del resto de las provincias.** Hoy solo Córdoba tiene Salud/Educación cargado; Buenos Aires está en `04 - Consolidadas.pdf` listo para procesar.
3. **Gasto funcional de Nación** (Presupuesto Abierto o Cuenta de Inversión) para comparar Salud/Educación entre niveles de gobierno.
4. **IPC** para poder mostrar series en pesos constantes. Sin ajuste por inflación, la serie 2005-2025 muestra que todo "creció" enormemente, lo cual es engañoso.

El punto 4 es importante para la honestidad del sitio: con inflación argentina, cualquier serie nominal de 21 años es prácticamente ilegible sin deflactar.

# Hallazgos del cruce Nación ↔ Córdoba

Resultado de cargar los 4 archivos en la base y verificar contra Postgres real.
**Estado: 325 filas cargadas, todos los controles en verde.**

---

## Lo que se cargó

| Jurisdicción | Universo | Tipo de dato | Filas | Años |
|---|---|---|---|---|
| Córdoba | central | presupuesto | 150 | 2010–2026 |
| Córdoba | apnf | presupuesto | 151 | 2010–2026 |
| Nación | apnf | ejecutado | 24 | 2026 |

El `.xls` que subiste resultó ser **mucho más valioso de lo esperado**: contiene 17 hojas, una por año desde 2010, ya en el esquema estandarizado de MECON y en millones de pesos. Es la serie histórica completa de Córdoba en un solo archivo. Y como MECON publica el mismo archivo para las 24 jurisdicciones, el mismo script sirve para las otras 4 provincias sin cambios.

---

## Los tres problemas de comparabilidad que aparecieron

Estos no son detalles técnicos: si el sitio los ignora, publica cifras incorrectas.

### 1. El universo institucional cambia el resultado 34 veces

Córdoba, presupuesto 2026, mismo indicador:

| Universo | Resultado financiero |
|---|---|
| Administración Central | **439.906 M** |
| Adm. Pública No Financiera (incluye Caja de Jubilaciones) | **12.996 M** |

La diferencia es la **Caja de Jubilaciones, que tiene déficit de -418.575 M**. Los PDFs del portal de Córdoba publican solo Administración Central; el consolidado de MECON incluye todo. Un titular tipo "Córdoba cerró con superávit de $439.906 M" es cierto solo si aclarás que excluye el sistema previsional.

Verifiqué que el PDF y el `.xls` reconcilian: PDF = 439.905 M, `.xls` columna Adm. Central = 439.906 M (diferencia por redondeo). Son la misma cosa medida igual.

**Solución aplicada:** campo `universo` obligatorio en cada fila. Ninguna consulta puede mezclarlos sin querer.

### 2. Presupuesto ≠ Ejecutado

Los datos de Córdoba son **presupuesto** (lo que se planea gastar, aprobado por ley). La Base Caja de Nación es **ejecutado** (lo que realmente se gastó). Graficar ambos en la misma serie sin aclararlo sería engañoso — los gobiernos suelen ejecutar menos de lo presupuestado.

**Solución aplicada:** campo `tipo_dato` obligatorio.

### 3. Unidades distintas

Los PDFs de Córdoba están en **pesos** (11.442.371.759.000); Nación y el consolidado MECON en **millones**. Un error acá multiplica todo por un millón.

**Solución aplicada:** todo se normaliza a millones al cargar, y se guarda `unidad_origen` para trazabilidad.

---

## Problema encontrado en el archivo de MECON

**La hoja 2021 es una copia exacta de la hoja 2020.** Lo verifiqué celda por celda: 220 celdas numéricas idénticas, 0 diferencias. Además el título de esa hoja dice "PRESUPUESTO 2021 LEY Nº" con el número de ley **vacío**, mientras que todas las demás lo tienen.

MECON aparentemente publicó esa hoja sin actualizarla. Si la cargabas sin revisar, tu sitio mostraría datos de 2020 etiquetados como 2021.

**Solución aplicada:** el script detecta este patrón automáticamente, avisa y omite el año. Córdoba quedó con 16 años cargados en vez de 17. Si querés cargarlo igual (marcándolo como provisorio), se hace con `omitir_duplicados=False`.

Vale la pena chequear si el mismo problema aparece en los archivos de las otras provincias — el control ya corre solo.

---

## Sobre comparar "gasto en Salud" entre Nación y Córdoba

Acá hay un límite que conviene tener claro desde ahora: **con estas fuentes no se puede hacer directamente.**

- Córdoba publica clasificación **funcional** (Salud, Educación, Seguridad) → la Planilla 04 que subiste.
- La Base Caja mensual de Nación publica clasificación **económica** (salarios, transferencias, subsidios) → no tiene una línea "Salud".

Son dos sistemas de clasificación distintos, no dos formatos del mismo dato. Para tener el gasto funcional de Nación hace falta otra fuente (Cuenta de Inversión o Presupuesto Abierto, que sí publican por finalidad y función).

Dejé la vista `vw_comparador_funcional` filtrando solo clasificación funcional, así el sitio no puede armar sin querer una comparación inválida. Hoy devuelve solo Córdoba; cuando carguemos el gasto funcional de Nación, aparece automáticamente.

---

## Gasto funcional de Córdoba 2026 (presupuesto, Adm. Central)

Extraído del PDF 04.0, control de suma contra el Total General: **0,0000% de diferencia**.

| Finalidad | Monto (M $ARS) |
|---|---|
| Servicios Sociales | 5.239.865 |
| Administración Gubernamental | 3.253.192 |
| Servicios Económicos | 1.579.273 |
| Servicios de Seguridad y Justicia | 1.560.776 |
| Deuda Pública | 2.185 |
| A Clasificar | -192.920 |

Desagregado (nivel 2):

| Función | Monto (M $ARS) |
|---|---|
| Educación y Cultura | 3.500.314 |
| Seguridad Interior | 1.232.265 |
| Salud | 1.208.065 |
| Promoción y Asistencia Social | 388.409 |
| Sistema Penal | 280.801 |
| Justicia | 12.384 |

Dato para el sitio: **Córdoba presupuesta casi 3 veces más en Educación que en Salud**, y el conjunto de Servicios Sociales se lleva el 46% del gasto total.

---

## Bugs corregidos durante la prueba

Los tres los encontró el propio proceso de verificación, no revisión a ojo:

1. **Columna TOTAL mal detectada.** Usaba la última columna por posición; la hoja 2020 trae columnas vacías de relleno al final, así que perdía el universo `apnf`. Ahora se detecta por encabezado.
2. **Hoja "2014 " con espacio final** rompía la búsqueda por nombre. Resuelto con un normalizador.
3. **Extracción del PDF tomaba el subtotal equivocado.** La Planilla 04 reparte los objetos del gasto en dos bloques de páginas y solo el segundo trae la columna "Total General"; mi heurística inicial tomaba el subtotal del primer bloque. Daba 0,55% de error — chico pero suficiente para que los números no cierren. Ahora identifica la página correcta por su encabezado y el control da 0,0000%.

El tercero es el más relevante: **sin el control de suma automático, ese error pasaba desapercibido.** Por eso conviene que cada adaptador nuevo traiga su propia verificación contra un total publicado.

---

## Próximos pasos

1. **Cargar las otras 4 jurisdicciones** (CABA, Buenos Aires, Santa Fe, Mendoza). El `.xls` de MECON tiene el mismo formato para todas — `ingesta_cordoba.py` sirve casi sin cambios, solo hay que parametrizar la jurisdicción. Bajalos de la misma página de "Presupuestos provinciales".
2. **Conseguir el gasto funcional de Nación** (Presupuesto Abierto o Cuenta de Inversión) para habilitar la comparación Salud/Educación entre niveles de gobierno.
3. **Cargar población** por jurisdicción y año en `indicadores_contexto` — sin eso no funcionan los rankings per cápita, que es el feature más potente para el público general.
4. Definir si el sitio muestra por defecto universo `central` o `apnf`, y mostrarlo siempre de forma visible en la interfaz.

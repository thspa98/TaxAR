# TaxAR

Sitio de transparencia fiscal de Argentina: qué gastan las 24 jurisdicciones, de dónde
sacan la plata y cómo se comparan entre sí — con datos oficiales y explicaciones para
alguien que no estudió economía.

---

## Cómo actualizar los datos

Es lo que vas a hacer una o dos veces por año. Son tres pasos.

**1. Descargá el archivo nuevo** y guardalo en `fuentes/`, reemplazando el viejo.
Los enlaces oficiales están en `etl/fuentes.py` y también en la página
*Cómo se calcula* del sitio.

**2. Si el archivo cambió de nombre**, abrí `etl/fuentes.py` y actualizá tres campos:

```python
"serie_aif": {
    "archivo": "serie_aif-apnf-2026.xlsx",   # <- el nombre nuevo
    "cobertura": "24 jurisdicciones, 2005-2026, ...",
    "revisado": "2027-03-15",                 # <- la fecha de hoy
}
```

**3. Regenerá los datos y publicá:**

```bash
python etl/exportar_json.py
cd web && npm run build
```

Eso es todo. No hace falta tocar ninguna página: los rankings, los gráficos y los
textos que mencionan años o cifras se recalculan solos a partir de los JSON.

### Si algo sale mal

El script corre ocho controles antes de escribir nada. Si alguno da **ERROR**, no se
genera ningún archivo y el mensaje te dice qué revisar. Los casos más comunes:

| Mensaje | Qué pasó | Cómo se arregla |
|---|---|---|
| `Sin datos fiscales: ...` | Cambió el nombre de una hoja del Excel | Agregá la grafía nueva en `HOJA_AIF`, en `etl/jurisdicciones.py` |
| `Sin población: ...` | INDEC escribió mal el nombre de una provincia | Agregá el alias en `ALIAS_INDEC`, en el mismo archivo |
| `la suma ... no coincide con el Consolidado` | Cambió la estructura de filas del AIF | Revisá `MAPEO_AIF` en `etl/taxonomia.py` |

Los **AVISOS** no frenan la publicación: son limitaciones conocidas que el sitio
muestra al lector en la página de metodología.

---

## Cómo está organizado

```
taxar/
├── fuentes/          Los archivos oficiales, tal como los publica cada organismo.
│                     No se editan nunca: son la prueba de dónde salió cada número.
│
├── etl/              Convierte esos archivos en los datos del sitio.
│   ├── fuentes.py         ← EL ÚNICO QUE TOCÁS PARA ACTUALIZAR
│   ├── jurisdicciones.py  Nombres, slugs y alias de las 24 jurisdicciones
│   ├── taxonomia.py       Cómo se llama cada concepto en castellano común
│   ├── lectores.py        Un lector por fuente
│   ├── controles.py       Verificación automática antes de publicar
│   ├── exportar_json.py   Orquesta todo y escribe los JSON
│   └── postgres/          Ingestas hacia Supabase (ver abajo)
│
├── sql/              Esquema de la base: 8 tablas y 7 vistas
│
├── web/              El sitio (Astro + React)
│   └── src/
│       ├── data/        JSON generados por el ETL — no se editan a mano
│       ├── lib/         Acceso a datos y formato de números
│       ├── components/  Piezas reutilizables; charts/ son islas React
│       ├── layouts/     Estructura común de las páginas
│       └── pages/       Una página = un archivo
│
└── docs/             Documentos de diseño y hallazgos del proyecto
```

La idea de fondo: **los datos entran por un solo lado y salen por un solo lado.**
Ninguna página del sitio hace cuentas propias — todas leen números ya calculados por
el ETL. Así, si una cifra está mal, hay un único lugar donde arreglarla.

---

## Por qué el sitio no consulta una base de datos

La serie fiscal se actualiza una vez al año y el IPC una vez al mes. Consultar una
base para servir un número que no cambió en once meses no aporta nada y agrega cosas
que se pueden romper.

En cambio, generar archivos JSON versionados junto al código tiene tres ventajas que
importan justamente en un sitio de transparencia:

- **Cada versión del dato queda registrada.** Se puede demostrar qué decía el sitio en
  cualquier fecha pasada.
- **Google indexa los números.** Un sitio que arma sus tablas con JavaScript en el
  navegador es invisible para los buscadores.
- **No se cae.** No hay servidor de base de datos del que dependa.

Supabase sigue siendo la base donde conviene procesar y auditar los datos, y los
scripts para cargarla están en `etl/postgres/`. Cuando el sitio sume encuestas y
quiz —que sí necesitan escribir— ahí va a hablar con Supabase en vivo, pero sólo
para eso.

---

## Cómo correr el sitio

```bash
cd web
npm install     # una sola vez
npm run dev     # http://localhost:4321
npm run build   # genera dist/ listo para subir
```

El resultado de `npm run build` es HTML estático: se puede publicar gratis en Vercel,
Netlify, Cloudflare Pages o GitHub Pages sin configurar nada.

Requiere Node 18 o superior y Python 3.9 o superior con `openpyxl` y `xlrd`:

```bash
pip install openpyxl xlrd
```

---

## Qué hay hecho y qué falta

**Hecho**

- 24 jurisdicciones × 21 años (2005–2025) de ejecución presupuestaria
- Población ajustada al Censo 2022 y gasto por habitante
- Dependencia de la Nación, los 21 años
- Serie deflactada por IPC regional (2017 en adelante)
- Ocho controles de calidad automáticos
- Páginas: inicio, ranking por habitante, dependencia, metodología

**Falta**

1. **IPC anterior a 2017.** La serie oficial arranca en dic-2016 y el índice de
   2007–2015 está cuestionado por la intervención del INDEC. Completarlo exige elegir
   una fuente alternativa (San Luis, CABA o series privadas) y explicitar la decisión
   en el sitio.
2. **Población 2005–2009.** Las proyecciones arrancan en 2010.
3. **Gasto por finalidad del resto de las provincias.** Hoy sólo Córdoba. Buenos Aires
   ya está en `04 - Consolidadas.pdf`, sin procesar.
4. **Desglose de impuestos provinciales** (Ingresos Brutos, Inmobiliario, Automotor,
   Sellos). La serie AIF los trae agregados.
5. **Fichas por provincia**, comparador de a dos, quiz y encuestas.

---

## Regla del proyecto

Toda fuente nueva trae **su propio control** contra un total publicado por el organismo,
más un control de cobertura que confirme que no falta ninguna jurisdicción.

No es burocracia. Los cuatro errores más graves que aparecieron acá no los encontró
nadie leyendo las planillas:

- La Pampa 2025 venía toda en cero y habría aparecido como la provincia que menos gasta
  del país.
- La hoja de Córdoba 2021 era copia exacta de la de 2020.
- INDEC escribió "SANTE FE" y Santa Fe —tercera economía provincial— desaparecía de
  todos los rankings por habitante sin que saltara ningún error.
- Una extracción de PDF tomaba el subtotal del bloque de páginas equivocado: 0,55% de
  diferencia, imposible de ver a ojo.

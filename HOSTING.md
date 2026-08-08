# TaxAR — traspaso para decidir el hosting

Documento para llevar a otro chat. Contiene todo lo que hace falta saber sobre el
proyecto para elegir dónde publicarlo, más una auditoría de código previa al lanzamiento.

---

## Qué es TaxAR

Sitio de transparencia fiscal de Argentina para público general: cuánto gasta cada
provincia, en qué lo gasta, cuánto cobra de impuestos y cuánto depende de la Nación.
Datos oficiales del Ministerio de Economía e INDEC, explicados en castellano común.

Estado: **listo para publicar**. Falta sólo decidir dónde.

---

## Lo único que importa para elegir hosting

**Es un sitio 100% estático.** No hay backend, no hay base de datos, no hay API, no hay
sesiones ni login. `npm run build` produce una carpeta `dist/` con HTML, CSS, JS e
imágenes, y eso es todo lo que hay que servir.

| Dato | Valor |
|---|---|
| Framework | Astro 5 (SSG puro, `output: 'static'`) |
| Páginas generadas | 38 |
| Peso total de `dist/` | 5,7 MB |
| Página más pesada | 231 KB de HTML (`/provincias`) |
| JS que descarga la home | 149 KB sin comprimir, 3 archivos |
| Runtime en el servidor | ninguno |
| Variables de entorno | ninguna |
| Dependencias externas en runtime | Google Fonts (2 familias) |
| Build | Node 18+, `npm ci && npm run build`, ~15 segundos |
| Tráfico esperado | desconocido; sitio nuevo |

**Consecuencia práctica:** cualquier hosting de estáticos alcanza. No hace falta
servidor, ni contenedor, ni serverless. El costo debería ser cero o casi cero hasta
volúmenes altos de tráfico.

---

## Cosas a tener en cuenta al elegir

### 1. El público es argentino
Conviene un CDN con presencia o buena latencia en Sudamérica. Es el único criterio
técnico que puede diferenciar a un proveedor de otro en este proyecto.

### 2. Va a tener picos impredecibles
Si una nota se comparte en X o la levanta un medio, el tráfico puede multiplicarse por
mil en una hora. Interesa saber **qué pasa cuando se pasa del plan gratuito**: hay
proveedores que cortan el sitio y otros que cobran. Para un proyecto sin ingresos, que
corte es preferible a una factura sorpresa — pero conviene decidirlo a conciencia.

### 3. El dominio
El sitio está configurado con `site: 'https://taxar.ar'` en `astro.config.mjs`. Si el
dominio final es otro, hay que cambiarlo ahí (afecta al sitemap y a las URLs canónicas).
El `.ar` se registra en NIC Argentina.

### 4. Actualizaciones
Los datos se actualizan una o dos veces al año corriendo un script de Python y
recompilando. No hace falta CI/CD sofisticado, pero **conectar el repositorio para que
publique solo al hacer push** ahorra bastante fricción.

### 5. Nada que proteger
No hay datos de usuarios, ni formularios, ni cookies, ni analytics instalado. Eso
simplifica mucho el cumplimiento y descarta preocupaciones de privacidad.

---

## Cómo se compila

```bash
cd web
npm ci
npm run build        # genera web/dist/
```

Node 18 o superior. El comando de build no necesita red más allá de npm.

Para regenerar los datos desde las fuentes oficiales (paso previo, sólo cuando hay
archivos nuevos):

```bash
pip install openpyxl xlrd
python etl/exportar_json.py
```

---

## Auditoría de código previa al lanzamiento

### Seguridad

| Chequeo | Resultado |
|---|---|
| `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`, `document.write` | ninguno |
| `target="_blank"` sin `rel="noopener"` | ninguno |
| Claves, tokens, contraseñas o cadenas de conexión en el repo | ninguno |
| Entrada de usuario que llegue a la página | ninguna (el único input es un buscador que filtra un array en memoria) |
| Formularios, cookies, almacenamiento local | ninguno |
| Dependencias en runtime | Google Fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) |
| Enlaces externos | sólo `x.com` en el pie |

**Superficie de ataque: prácticamente nula.** Es HTML estático sin entrada de usuario
ni estado en servidor. El riesgo se limita a lo que pueda pasar en la cuenta del
hosting o del registrador del dominio, así que conviene activar autenticación en dos
pasos en ambos.

Una nota sobre `mapa-argentina.js` (561 KB, en `web/public/assets/`): es código de
terceros que se ejecuta en el navegador. Fue revisado, no hace peticiones de red ni
accede a almacenamiento, y sólo dibuja SVG. Vale saber que está ahí.

### Código muerto

Se eliminó en esta pasada:

- `ISO_MAPA` en `etl/jurisdicciones.py` — quedó huérfano al pasar del mapa de
  simplemaps al del IGN.
- Tres funciones exportadas que nunca se llamaron desde ninguna página:
  `estaAtrasada()`, `avisos()` y `rankingsDelAnio()`.
- `SERIES`, `RANKINGS` y `SIN_REPORTE` pasaron de `export` a privadas: se usan sólo
  dentro de `datos.ts`, a través de las funciones que sí se exportan.
- `ANIO_COMPLETO`, que dejó de tener sentido cuando el sitio pasó a priorizar el año
  más reciente sobre el año completo.
- Cachés de Python (`etl/__pycache__/`).

**Quedan dos archivos por borrar a mano** (el entorno no tuvo permisos):

```
web/src/components/charts/MapaArgentina.jsx   ← el mapa viejo, reemplazado por MapaIGN.jsx
fuentes/mapa_argentina.svg                    ← el SVG de simplemaps, reemplazado por el del IGN
```

Ninguno de los dos se importa desde ningún lado, así que no rompen nada, pero conviene
sacarlos antes de publicar el repositorio.

### Rendimiento

- 149 KB de JS en la home (3 archivos). La mayor parte es React más Recharts.
- Los gráficos usan carga diferida: un ranking plegado no descarga Recharts hasta que
  se abre.
- `mapa-argentina.js` se carga sólo en las tres páginas que tienen mapa.
- Las páginas más pesadas (~230 KB de HTML) lo son porque llevan los datos embebidos
  para que Google los indexe. Comprimidos con gzip quedan en una fracción.

### Accesibilidad y SEO

- Todas las páginas tienen `<title>`, `meta description` y Open Graph.
- Los números están en el HTML, no generados por JavaScript: los buscadores los leen.
- Navegación por teclado en el menú, el mapa, los desplegables y las tablas ordenables.
- Los desplegables usan `<details>` nativo, así que el contenido se indexa aunque esté
  cerrado.
- Se respeta `prefers-reduced-motion` en todas las animaciones.

**Falta antes de publicar:** no hay `sitemap.xml` ni `robots.txt`. Astro los genera con
`@astrojs/sitemap`; conviene agregarlo en el mismo paso que el hosting.

---

## Obligaciones legales pendientes

Dos cosas que **no** están resueltas y conviene mirar antes de un lanzamiento público:

1. **Mapa del Instituto Geográfico Nacional.** Los términos del IGN exigen la leyenda
   "FUENTE: Instituto Geográfico Nacional de la República Argentina" —ya está visible al
   pie de cada mapa— y prohíben modificar límites o suprimir toponimia, cosa que no se
   hizo. Pero además mencionan un **trámite de aprobación de la obra ante el IGN** para
   uso público. Ese trámite no se inició.

2. **Alícuotas provinciales.** Son una compilación propia a partir de las leyes
   impositivas, no una publicación oficial. El sitio lo aclara y pide que reporten
   errores, pero todavía no tienen la norma y el enlace al boletín oficial de cada
   provincia cargados fila por fila.

Ninguna de las dos impide publicar, pero conviene que las mire alguien con criterio
legal si el sitio va a tener difusión.

---

## Estructura del proyecto

```
taxar/
├── fuentes/          Archivos oficiales sin modificar (XLSX del MECON, INDEC, mapa IGN)
├── etl/              Python: lee las fuentes, corre 17 controles, escribe los JSON
│   └── fuentes.py    ← el único archivo que se toca para actualizar datos
├── sql/              Esquema Postgres (opcional, no lo usa el sitio)
├── docs/             Documentos de diseño y hallazgos
└── web/              El sitio
    ├── public/assets/  logo y mapa-argentina.js
    ├── src/data/       JSON generados por el ETL (no se editan a mano)
    ├── src/lib/        acceso a datos y formato de números
    ├── src/components/ piezas reutilizables; charts/ son islas React
    ├── src/layouts/    estructura común
    └── src/pages/      una página = un archivo
```

Los datos entran por un solo lado y salen por un solo lado: ninguna página hace cuentas
propias, todas leen números ya calculados por el ETL. Si una cifra está mal, hay un
único lugar donde arreglarla.

---

## Qué preguntar en el otro chat

Para que la recomendación sea útil, conviene aclarar:

- **Presupuesto**: ¿tiene que ser gratis, o hay margen para unos dólares al mes?
- **Dominio**: ¿ya está registrado `taxar.ar`?
- **Repositorio**: ¿el código va a estar en GitHub/GitLab, público o privado?
- **Analytics**: ¿se quiere medir visitas? Si sí, conviene uno sin cookies para no
  tener que poner banner de consentimiento.
- **Qué pasa en un pico**: ¿se prefiere que el sitio se caiga o que genere costo?

Con eso alcanza para elegir bien.

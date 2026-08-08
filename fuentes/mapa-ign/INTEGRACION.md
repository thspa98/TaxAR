# Mapa interactivo de provincias argentinas

Componente sin dependencias (vanilla JS, 560 KB, 179 KB con gzip). No usa CDN, no usa d3,
no usa topojson: los `path` del SVG ya vienen calculados.

Interacción: se selecciona **haciendo click sobre la provincia en el mapa** (o con Tab + Enter).
Arrastrar desplaza el mapa y no selecciona. Rueda del mouse para zoom.

---

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `mapa_argentina_interactivo.html` | Demo completa en un solo archivo. Abrilo con doble click. |
| `mapa-argentina.js` | El componente. Es lo único que necesitás para integrar. |
| `provincias.json` | Las 24 provincias con `gid`, `nombre`, `indec`, `slug`. Para cruzar con tus datos. |
| `provincias-continental.svg` | SVG suelto, sin JS, un `<path>` por provincia. |
| `provincias-bicontinental.svg` | Igual, pero con el sector antártico completo. |

---

## Integración mínima

1. Copiá `mapa-argentina.js` a tus assets estáticos.
2. Pegá esto donde quieras el mapa:

```html
<div id="mapa" style="height: 620px"></div>
<script src="/assets/mapa-argentina.js"></script>
<script>
  const mapa = MapaArgentina.crear({
    el: '#mapa',
    maxSeleccion: 2,          // modo comparación
    onChange: (seleccion) => {
      // seleccion = [{gid, nombre, nombreCompleto, indec}, ...] en orden de click
      console.log(seleccion);
    }
  });
</script>
```

Dos requisitos del contenedor, los dos fáciles de pasar por alto:

- **Altura definida.** El componente ocupa el 100% del contenedor; si el `div` colapsa a 0 no
  vas a ver nada.
- **No le pongas `overflow: visible`.** El componente ya aplica `overflow: hidden`; si lo pisás
  desde afuera, el mapa se desborda al hacer zoom.

Nada más: no hay CSS externo que cargar ni dependencias que instalar.

---

## Opciones de `crear()`

| Opción | Default | Qué hace |
|---|---|---|
| `el` | — | Selector o nodo del contenedor. Obligatorio. |
| `maxSeleccion` | `2` | Máximo de provincias seleccionables. `0` = sin límite. |
| `modo` | `'cola'` | `'cola'`: la tercera libera la más vieja. `'bloquear'`: ignora la tercera. |
| `vista` | `'continental'` | `'continental'` (continente + Malvinas) o `'bicontinental'` (todo). |
| `zoom` | `true` | Rueda para zoom, arrastrar para desplazar. |
| `tooltip` | `true` | Etiqueta con el nombre al pasar el mouse. |
| `onChange` | — | `(seleccion) => {}` cada vez que cambia la selección. |
| `onHover` | — | `(provincia \| null) => {}` al entrar/salir de una provincia. |

## Métodos

```js
mapa.getSeleccion()                  // [{gid, nombre, nombreCompleto, indec}, ...]
mapa.setSeleccion(['50', '66'])      // acepta gid, código INDEC o nombre exacto
mapa.setSeleccion(['Mendoza', 'Salta'])
mapa.alternar('Córdoba')             // selecciona / deselecciona
mapa.limpiar()
mapa.provincias()                    // las 24, ordenadas alfabéticamente
mapa.colorear({ '06': '#c00', '50': '#f80' })   // mapa de calor
mapa.setVista('bicontinental')
mapa.enfocar('Jujuy')                // centra el viewBox en una provincia
mapa.restablecerVista()
mapa.nodo('Salta')                   // el <path>, por si querés manipularlo
mapa.destruir()
```

Cualquier método que reciba una provincia acepta las tres formas: `gid` (número interno del IGN),
código INDEC (`'06'`, `'94'`…) o nombre exacto con tildes (`'Córdoba'`, no `'Cordoba'`).

Podés tener varias instancias en la misma página; son independientes.

---

## Cruzar con tus datos

El código INDEC es la clave recomendada: es el estándar oficial y lo vas a encontrar en
cualquier dataset público de AFIP/ARCA, INDEC o los ministerios provinciales.

```js
const alicuotas = { '06': 3.5, '50': 4.0, '94': 3.0 };  // por código INDEC

MapaArgentina.crear({
  el: '#mapa',
  maxSeleccion: 2,
  onChange: ([a, b]) => {
    if (!a || !b) return;
    render(alicuotas[a.indec], alicuotas[b.indec]);
  }
});
```

Para un mapa de calor sobre los mismos datos:

```js
mapa.colorear(
  Object.fromEntries(
    Object.entries(alicuotas).map(([indec, v]) => [indec, escalaDeColor(v)])
  )
);
```

---

## Estilos

Todo el CSS está namespaced bajo `.mapar` y `.mapar__*`, así que no choca con tus estilos.
Los colores se cambian con custom properties sobre el contenedor:

```css
#mapa {
  --mapar-fill: #9dc4e8;      /* provincia sin seleccionar */
  --mapar-hover: #6fa5d6;
  --mapar-stroke: #ffffff;    /* línea divisoria */
  --mapar-stroke-w: 0.9;
  --mapar-sel-1: #0d47a1;     /* primera seleccionada */
  --mapar-sel-2: #f2711c;     /* segunda seleccionada */
}
```

La segunda selección va en naranja a propósito: sobre un territorio azul, dos azules distintos
se confunden y el comparador deja de leerse de un vistazo. Si preferís mantener todo en la misma
gama, `--mapar-sel-2: #4dd0e1` (celeste) es la alternativa que mejor contrasta.

El mapa nunca se dibuja fuera de su contenedor: se recorta al borde, el zoom no se aleja más allá
del mapa completo ni se acerca más allá de 1/25 de la vista, y el paneo no te deja perder el mapa
de vista.

Accesibilidad: cada provincia es un `role="button"` navegable con Tab, seleccionable con
Enter o Espacio, con `aria-pressed` y `aria-label`.

---

## Si usás React / Vue

El componente es agnóstico. En React:

```jsx
import { useEffect, useRef } from 'react';

export function MapaProvincias({ seleccion, onSeleccion }) {
  const ref = useRef(null);
  const inst = useRef(null);

  useEffect(() => {
    inst.current = window.MapaArgentina.crear({
      el: ref.current,
      maxSeleccion: 2,
      onChange: onSeleccion
    });
    return () => inst.current.destruir();
  }, []);

  useEffect(() => {
    inst.current?.setSeleccion(seleccion, true);  // true = no dispara onChange
  }, [seleccion]);

  return <div ref={ref} style={{ height: 620 }} />;
}
```

Cargá `mapa-argentina.js` con un `<script>` en el HTML, o importalo directo si tu bundler
lo permite (el archivo es UMD, así que también funciona con `require`/`import`).

---

## Sobre la geometría

- Fuente: capa **Provincia** del Instituto Geográfico Nacional, en WGS 84 (EPSG:4326).
- Proyección: cónica equivalente de Albers (`parallels [-20, -75]`, `rotate [65, 0]`),
  que preserva las áreas relativas entre provincias.
- Simplificación al 1% con mapshaper (`keep-shapes`), de ~4 millones de puntos a un tamaño
  apto para web. Las 24 provincias y todas las islas se conservan.
- Tierra del Fuego, Antártida e Islas del Atlántico Sur es **una sola provincia** e incluye
  Isla Grande, Malvinas, Georgias del Sur, Sandwich del Sur y el Sector Antártico Argentino.
  Al seleccionarla se resaltan todas sus partes a la vez, que es el comportamiento correcto.
- La vista `continental` es un recorte del `viewBox` (un zoom), no una edición de la geometría:
  nada se suprime ni se modifica.

---

## Si tocás el código de interacción, leé esto

Dos cosas rompieron el componente durante el desarrollo. Si alguien lo modifica, conviene que
las tenga presentes, porque las dos fallan de un modo silencioso.

### 1. Nada de `setPointerCapture` en el paneo

El paneo estaba implementado con `svg.setPointerCapture(ev.pointerId)` en el `pointerdown`.
Con la captura activa, el navegador **reapunta `pointerdown` y `pointerup` al elemento que
capturó**, y como el evento `click` se emite en el ancestro común de ambos, terminaba
disparándose en el `<svg>` en lugar del `<path>`. Resultado: el mapa se veía perfecto, el
paneo andaba, y las provincias no se podían seleccionar.

Ahora el paneo usa un **umbral de arrastre** (`UMBRAL = 4` px): por debajo de eso el gesto se
considera un click y no se toca el `viewBox`; por encima, se panea y se levanta la bandera
`arrastroRecien`, que hace que el handler de `click` ignore el click que el navegador emite
inmediatamente después. Sin captura de puntero, el `click` llega al `<path>` como corresponde.

### 2. El SVG necesita `overflow: hidden`

Con `overflow: visible` el SVG pinta **todo** su contenido, no solo lo que entra en el
`viewBox`. Al hacer zoom, el mapa se desbordaba fuera de la tarjeta y se superponía con el
resto de la página. Tanto `.mapar` como `.mapar__svg` llevan `overflow: hidden`.

Además hay un `clamp()` sobre el `viewBox`: el zoom no se aleja más allá del mapa completo ni
se acerca más allá de 1/25 de la vista base, y el centro del encuadre siempre queda dentro del
mapa, así que no se puede arrastrar el mapa fuera de cuadro.

### Verificación

Hay dos suites que corren con jsdom, sin acceso a red:

- **General (34 checks):** las 24 provincias renderizan, ningún path con `NaN`, la API de
  selección resuelve por gid / INDEC / nombre, `onChange` dispara, dos instancias no se pisan,
  el zoom y el paneo quedan acotados, y el HTML no referencia ningún recurso externo.
- **Interacción (11 checks):** reproduce la secuencia real del navegador
  (`pointerdown` → `pointermove` → `pointerup` → `click`) **incluida la regla de retargeting por
  pointer capture**, que es lo que había roto la selección. Verifica que un click selecciona,
  que un temblor de 2 px sigue contando como click, que un arrastre panea sin seleccionar, y
  que después de arrastrar el click vuelve a funcionar.

Si modificás el manejo de eventos, el test de interacción es el que te va a avisar: un test que
solo dispare `click` sintético **no detecta este bug**, porque salta toda la secuencia de
punteros. Fue exactamente lo que pasó la primera vez.

---

## Atribución obligatoria

Los términos del IGN exigen reconocer la autoría. La demo ya la incluye en el pie. Si armás
tu propio layout, tenés que mantener visible:

> **FUENTE: Instituto Geográfico Nacional de la República Argentina.**

Y además, según esos mismos términos:

- No se pueden modificar los límites internacionales, interprovinciales ni de espacios marítimos.
- No se puede suprimir ni alterar la identificación de las islas ni la toponimia marítima.
- El uso comercial se permite solo en obras derivadas, donde la información sea insumo de un
  producto nuevo. Un comparador de impuestos entra en esa categoría, pero conviene que lo
  confirmes vos.
- La plantilla normalizada no exime del trámite de aprobación de la obra ante el IGN.
  Si Taxar va a ser público, ese trámite corre por tu cuenta.

No soy abogado y esto no es asesoramiento legal: es lo que dicen los términos que me pasaste.
Para un sitio público conviene que lo revise alguien especializado.

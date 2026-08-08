/**
 * noticias.ts — El índice de las notas.
 *
 * Acá viven los METADATOS de cada nota; el texto vive en su propia página bajo
 * `src/pages/noticias/`. Se separan a propósito: el carrusel de la portada y el
 * listado necesitan título, fecha y portada, pero no el artículo entero.
 *
 * PARA PUBLICAR UNA NOTA NUEVA
 *   1. Copiá una página de `src/pages/noticias/` y escribí la tuya.
 *   2. Agregá su entrada acá arriba de todo (el orden de este array es el
 *      orden en que aparecen).
 *   3. Listo. Aparece sola en el carrusel de la portada y en /noticias.
 *
 * REGLA DE REDACCIÓN: cada nota tiene que apoyarse en un dato que el sitio ya
 * publica y poder enlazarlo. Si una afirmación no se puede verificar en una
 * página del sitio o en la fuente oficial, no va.
 */

export type Noticia = {
  slug: string;
  titulo: string;
  bajada: string;
  fecha: string;            // AAAA-MM-DD
  categoria: 'Análisis' | 'Explicador' | 'Dato del mes' | 'Transparencia';
  /** Cifra grande de la portada, generada con los datos del sitio. */
  cifra: string;
  cifraPie: string;
  /** Estilo de la portada ilustrada. */
  portada: 'barras' | 'mapa' | 'linea' | 'balanza' | 'aviso';
  minutos: number;
};

export const NOTICIAS: Noticia[] = [
  {
    slug: 'salud-por-habitante',
    titulo: 'Un neuquino recibe seis veces más presupuesto de salud que un bonaerense',
    bajada:
      'El gasto provincial en salud por habitante va de $787.750 a $122.545 según dónde vivas. ' +
      'La diferencia no la explica sólo la riqueza de cada provincia.',
    fecha: '2026-08-05',
    categoria: 'Análisis',
    cifra: '6,4x',
    cifraPie: 'entre la primera y la última',
    portada: 'barras',
    minutos: 4,
  },
  {
    slug: 'coparticipacion-congelada',
    titulo: 'El reparto de la coparticipación se escribió en 1988 y nadie lo tocó desde entonces',
    bajada:
      'Buenos Aires tiene el 38,5% de la población del país y recibe el 23% de la coparticipación. ' +
      'Tierra del Fuego, el 0,43% de la gente y el 1,18% del dinero.',
    fecha: '2026-08-04',
    categoria: 'Explicador',
    cifra: '38 años',
    cifraPie: 'sin actualizar los coeficientes',
    portada: 'balanza',
    minutos: 6,
  },
  {
    slug: 'gasto-bonaerense-inflacion',
    titulo: 'El gasto de Buenos Aires se multiplicó por 66 y aun así cayó',
    bajada:
      'Es el ejemplo más claro de por qué una serie en pesos corrientes puede llevar a la ' +
      'conclusión exactamente opuesta a la realidad.',
    fecha: '2026-08-03',
    categoria: 'Análisis',
    cifra: '−16%',
    cifraPie: 'descontada la inflación',
    portada: 'linea',
    minutos: 5,
  },
  {
    slug: 'ingresos-brutos-donde-se-paga-mas',
    titulo: 'El mismo comercio paga 3,5% en Corrientes y 5% en Buenos Aires',
    bajada:
      'Ingresos Brutos es el impuesto provincial que más recaudás sin darte cuenta: no figura ' +
      'en el ticket, pero está adentro del precio de casi todo.',
    fecha: '2026-08-02',
    categoria: 'Explicador',
    cifra: '3,5% a 5%',
    cifraPie: 'según la provincia',
    portada: 'mapa',
    minutos: 4,
  },
  {
    slug: 'la-pampa-no-reporto',
    titulo: 'La Pampa no informó cuánto gastó en 2025, y eso también es un dato',
    bajada:
      'Cuando una provincia no reporta, la mayoría de los sitios la carga en cero o la borra ' +
      'de la tabla. Las dos cosas mienten.',
    fecha: '2026-08-01',
    categoria: 'Transparencia',
    cifra: '23 de 24',
    cifraPie: 'jurisdicciones reportaron 2025',
    portada: 'aviso',
    minutos: 3,
  },
];

export const CATEGORIA_COLOR: Record<string, string> = {
  'Análisis': '#2D4A7A',
  'Explicador': '#0F766E',
  'Dato del mes': '#D4AF37',
  'Transparencia': '#B45309',
};

export function noticia(slug: string) {
  return NOTICIAS.find((n) => n.slug === slug)!;
}

export function otras(slug: string, cuantas = 3) {
  return NOTICIAS.filter((n) => n.slug !== slug).slice(0, cuantas);
}

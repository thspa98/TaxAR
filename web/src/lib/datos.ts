/**
 * datos.ts — La única puerta de entrada a los datos.
 *
 * Ninguna página importa un JSON directamente: todas pasan por acá. Así, el
 * día que los datos dejen de venir de archivos y pasen a venir de Supabase,
 * se cambia este archivo y las páginas no se enteran.
 */

import meta from '../data/meta.json';
import jurisdiccionesJson from '../data/jurisdicciones.json';
import seriesJson from '../data/series.json';
import categoriasJson from '../data/categorias.json';
import rankingsJson from '../data/rankings.json';
import glosarioJson from '../data/glosario.json';
import ipcJson from '../data/ipc.json';
import mapaJson from '../data/mapa.json';
import alicuotasJson from '../data/alicuotas.json';
import finalidadJson from '../data/finalidad.json';

export type Fila = {
  anio: number;
  ingresos_totales: number | null;
  gastos_totales: number | null;
  gastos_primarios: number | null;
  resultado_financiero: number | null;
  resultado_primario: number | null;
  resultado_economico: number | null;
  intereses: number | null;
  poblacion: number | null;
  gasto_per_capita: number | null;
  ingreso_per_capita: number | null;
  gastos_constantes: number | null;
  ingresos_constantes: number | null;
  deflactor: number | null;
  dependencia_nacion: number | null;
  impuestos_propios: number | null;
  impuestos_por_habitante: number | null;
  coparticipacion: number | null;
  coparticipacion_por_habitante: number | null;
  share_coparticipacion?: number;
  share_poblacion?: number;
  indice_reparto?: number;
  resultado_sobre_ingresos: number | null;
};

export type Jurisdiccion = {
  slug: string;
  nombre: string;
  corto: string;
  indec: string;
  region: string;
  gentilicio: string;
  poblacion: Record<string, number>;
  ultimo_anio: number | null;
  censo2022: number | null;
  ajuste_censal: { factor: number | null; desvio_pct: number | null; proyeccion_indec_2022: number | null };
};

export type EntradaRanking = { slug: string; valor: number; puesto: number };
export type Control = { control: string; severidad: 'ok' | 'aviso' | 'error'; detalle: string };

export const META = meta as any;
export const JURISDICCIONES = jurisdiccionesJson as unknown as Record<string, Jurisdiccion>;
const SERIES = seriesJson as unknown as Record<string, Fila[]>;
export const CATEGORIAS = categoriasJson as unknown as Record<string, Record<string, Record<string, number>>>;
const RANKINGS = rankingsJson as unknown as Record<string, Record<string, EntradaRanking[]>>;
export const GLOSARIO = glosarioJson as any;
export const IPC = ipcJson as any;
export const MAPA = mapaJson as unknown as {
  indec_a_slug: Record<string, string>;
  slug_a_indec: Record<string, string>;
  nombres_ign: Record<string, string>;
  fuente: { nombre: string; organismo: string; url: string; cobertura: string };
  atribucion: string;
  nota_territorio: string;
};

export type Rubro = { etiqueta: string; explica: string; color: string };

/** En qué gasta cada provincia: 5 finalidades y 9 funciones dentro de la social. */
export const FINALIDAD = finalidadJson as unknown as {
  finalidades: Record<string, Rubro>;
  funciones: Record<string, Rubro>;
  anios_estimados: number[];
  nota_estimados: string;
  fuente: { nombre: string; organismo: string; url: string; cobertura: string };
  datos: Record<string, Record<string, number | boolean>[]>;
  rankings: Record<string, Record<string, EntradaRanking[]>>;
};

/** Años con gasto por finalidad. Termina un año antes que la serie fiscal. */
export const ANIOS_FF: number[] = Object.keys(FINALIDAD.rankings)
  .map(Number).sort((a, b) => a - b);
export const ANIO_FF: number = Math.max(...ANIOS_FF);

export function finalidadDe(slug: string, anio: number = ANIO_FF) {
  return FINALIDAD.datos[slug]?.find((f) => f.anio === anio) as
    (Record<string, number> & { estimado: boolean }) | undefined;
}

export function rankingFF(campo: string, anio: number = ANIO_FF): EntradaRanking[] {
  return FINALIDAD.rankings[String(anio)]?.[campo] ?? [];
}

export function puestoFF(campo: string, slug: string, anio: number = ANIO_FF): number | null {
  return rankingFF(campo, anio).find((r) => r.slug === slug)?.puesto ?? null;
}

export function rankingFFConNombres(campo: string, anio: number = ANIO_FF) {
  return rankingFF(campo, anio).map((r) => ({
    ...r,
    nombre: jur(r.slug).corto,
    nombreLargo: jur(r.slug).nombre,
    region: jur(r.slug).region,
  }));
}

export type Alicuota = { min: number; max: number; rango: boolean };
export const ALICUOTAS = alicuotasJson as unknown as {
  impuestos: Record<string, {
    etiqueta: string; corto: string; explica: string;
    quien: string; base: string; color: string;
  }>;
  orden: string[];
  bases: Record<string, {
    etiqueta: string; estandar: string; por_que_importa: string;
    variantes: [string, string][]; especiales: string[];
  }>;
  datos: Record<string, Record<string, Alicuota>>;
  fuente: { nombre: string; organismo: string; cobertura: string; revisado: string };
  revisada_por_terceros: boolean;
  advertencia: string;
};

/**
 * Año que encabeza el sitio: el MÁS RECIENTE disponible.
 *
 * Puede faltarle alguna jurisdicción que no reportó. No se oculta: `SIN_REPORTE`
 * dice quién falta en cada año y el sitio lo aclara donde corresponde.
 */
export const ANIO_ACTUAL: number = META.cobertura.anio_referencia;
const SIN_REPORTE: Record<string, string[]> = META.cobertura.sin_reporte ?? {};
export const ANIOS: number[] = Object.keys(RANKINGS).map(Number).sort((a, b) => a - b);

/** Quiénes no reportaron un año dado. */
export function faltantes(anio: number = ANIO_ACTUAL): string[] {
  return SIN_REPORTE[String(anio)] ?? [];
}

/** Último año con dato propio de una jurisdicción. */
export function ultimoAnio(slug: string): number {
  return JURISDICCIONES[slug].ultimo_anio ?? ANIO_ACTUAL;
}


/** Frase lista para mostrar cuando falta alguien. */
export function avisoFaltantes(anio: number = ANIO_ACTUAL): string | null {
  const f = faltantes(anio);
  if (!f.length) return null;
  const nombres = f.map((s) => JURISDICCIONES[s].nombre);
  const lista = nombres.length === 1
    ? nombres[0]
    : `${nombres.slice(0, -1).join(', ')} y ${nombres.at(-1)}`;
  return `${lista} ${nombres.length === 1 ? 'todavía no reportó' : 'todavía no reportaron'} ${anio}: ` +
    `${nombres.length === 1 ? 'su última cifra disponible es de' : 'sus últimas cifras disponibles son de'} ` +
    `${Math.max(...f.map((s) => JURISDICCIONES[s].ultimo_anio ?? anio))}.`;
}

export function jur(slug: string): Jurisdiccion {
  return JURISDICCIONES[slug];
}

export function fila(slug: string, anio: number): Fila | undefined {
  return SERIES[slug]?.find((f) => f.anio === anio);
}

export function ranking(tipo: string, anio: number = ANIO_ACTUAL): EntradaRanking[] {
  return RANKINGS[String(anio)]?.[tipo] ?? [];
}

/** Ranking con el nombre ya resuelto: lo que consume un gráfico. */
export function rankingConNombres(tipo: string, anio: number = ANIO_ACTUAL) {
  return ranking(tipo, anio).map((r) => ({
    ...r,
    nombre: jur(r.slug).corto,
    nombreLargo: jur(r.slug).nombre,
    region: jur(r.slug).region,
  }));
}

/** En qué puesto salió una jurisdicción en un ranking dado. */
export function puesto(tipo: string, slug: string, anio: number = ANIO_ACTUAL): number | null {
  return ranking(tipo, anio).find((r) => r.slug === slug)?.puesto ?? null;
}

export function serie(slug: string): Fila[] {
  return SERIES[slug] ?? [];
}


export function explicacion(clave: string): { etiqueta: string; explica: string } | undefined {
  return GLOSARIO.conceptos[clave] ?? GLOSARIO.categorias[clave];
}


export type Destacado = {
  slug: string;
  jurisdiccion: string;
  titulo: string;
  cifra: string;
  detalle: string;
  href: string;
  tono?: 'oro' | 'superavit' | 'deficit' | 'neutro';
};

/**
 * Los hechos más relevantes del año, uno por jurisdicción.
 *
 * Se arma una lista de candidatos ordenada por cuánto dice cada hecho, y se
 * eligen de arriba hacia abajo salteando las jurisdicciones ya usadas. Así el
 * bloque nunca repite provincia —que sería aburrido y daría la impresión de que
 * el país son tres provincias— salvo que se agoten los hechos importantes.
 *
 * Todo sale de los datos: si el año que viene cambian los primeros puestos,
 * cambian solos.
 */
export function destacados(anio: number = ANIO_ACTUAL, cuantos = 5): Destacado[] {
  const fm = (v: number, d = 0) =>
    v.toLocaleString('es-AR', { minimumFractionDigits: d, maximumFractionDigits: d });

  const pc = ranking('gasto_per_capita', anio);
  const dep = ranking('dependencia_nacion', anio);
  const imp = ranking('impuestos_por_habitante', anio);
  const res = ranking('resultado_sobre_ingresos', anio);
  const tot = ranking('gasto_total', anio);
  if (!pc.length) return [];

  const n = (s: string) => jur(s).nombre;
  const c = (s: string) => jur(s).corto;

  const candidatos: (Destacado | null)[] = [
    // 1. La brecha por habitante: el dato que reordena todo lo demás.
    {
      slug: pc[0].slug,
      jurisdiccion: n(pc[0].slug),
      titulo: 'La que más gasta por habitante',
      cifra: `$${fm(pc[0].valor)}`,
      detalle: `Gasta ${fm(pc[0].valor / pc.at(-1)!.valor, 1)} veces lo de ${c(pc.at(-1)!.slug)}, que es la última del ranking.`,
      href: '/ranking/',
      tono: 'oro',
    },
    // 2. Dependencia máxima: explica el federalismo fiscal argentino.
    {
      slug: dep[0].slug,
      jurisdiccion: n(dep[0].slug),
      titulo: 'La que menos decide sobre su plata',
      cifra: `${fm(dep[0].valor, 1)}%`,
      detalle: `Esa proporción de los impuestos que maneja le llega de la Nación en vez de recaudarla ella. Depende ${fm(dep[0].valor / dep.at(-1)!.valor, 0)} veces más que ${c(dep.at(-1)!.slug)}.`,
      href: '/dependencia/',
    },
    // 3. Impuestos provinciales por habitante: lo que le sale al vecino.
    {
      slug: imp[0]?.slug,
      jurisdiccion: imp[0] ? n(imp[0].slug) : '',
      titulo: 'La que más cobra de impuestos por habitante',
      cifra: imp[0] ? `$${fm(imp[0].valor)}` : '',
      detalle: imp[0]
        ? `Recauda ${fm(imp[0].valor / imp.at(-1)!.valor, 1)} veces por habitante lo que recauda ${c(imp.at(-1)!.slug)} con sus propios impuestos.`
        : '',
      href: '/impuestos/',
    },
    // 4. El desequilibrio más grande del año.
    (() => {
      const peor = res.at(-1)!;
      return peor.valor < 0 ? {
        slug: peor.slug,
        jurisdiccion: n(peor.slug),
        titulo: 'La que más gastó de más',
        cifra: `${fm(peor.valor, 1)}%`,
        detalle: `Gastó ${fm(Math.abs(peor.valor), 1)}% más de lo que recaudó y tuvo que cubrir la diferencia con deuda o ayuda.`,
        href: `/provincia/${peor.slug}/`,
        tono: 'deficit' as const,
      } : null;
    })(),
    // 5. El contraste entre tamaño y gasto real por persona.
    (() => {
      const grande = tot[0];
      const p = puesto('gasto_per_capita', grande.slug, anio);
      return p && p > 3 ? {
        slug: grande.slug,
        jurisdiccion: n(grande.slug),
        titulo: 'La más grande no es la que más gasta',
        cifra: `1° y ${p}°`,
        detalle: `Primera en gasto total y ${p}ª por habitante: tiene el presupuesto más alto del país porque tiene la población más alta.`,
        href: '/ranking/',
      } : null;
    })(),
    // 6. El que mejor cerró sus cuentas.
    (() => {
      const mejor = res[0];
      return mejor.valor > 0 ? {
        slug: mejor.slug,
        jurisdiccion: n(mejor.slug),
        titulo: 'La que mejor cerró sus cuentas',
        cifra: `+${fm(mejor.valor, 1)}%`,
        detalle: `Le sobró el equivalente al ${fm(mejor.valor, 1)}% de todo lo que recaudó en el año.`,
        href: `/provincia/${mejor.slug}/`,
        tono: 'superavit' as const,
      } : null;
    })(),
    // 7. La otra punta de la dependencia.
    {
      slug: dep.at(-1)!.slug,
      jurisdiccion: n(dep.at(-1)!.slug),
      titulo: 'La que más se financia sola',
      cifra: `${fm(dep.at(-1)!.valor, 1)}%`,
      detalle: 'Es lo único que recibe de la Nación: el resto de los impuestos que maneja los recauda con sus propios contribuyentes.',
      href: '/dependencia/',
    },
    // 8. La punta baja del gasto por habitante.
    {
      slug: pc.at(-1)!.slug,
      jurisdiccion: n(pc.at(-1)!.slug),
      titulo: 'La que menos gasta por habitante',
      cifra: `$${fm(pc.at(-1)!.valor)}`,
      detalle: `Con la misma cantidad de habitantes que atender, dispone de mucho menos por persona que el promedio del país.`,
      href: '/ranking/',
    },
  ];

  const usadas = new Set<string>();
  const elegidos: Destacado[] = [];
  for (const d of candidatos) {
    if (!d || !d.slug || usadas.has(d.slug)) continue;
    usadas.add(d.slug);
    elegidos.push(d);
    if (elegidos.length === cuantos) break;
  }
  // Si se agotaron los hechos de jurisdicciones distintas, se completa
  // permitiendo repetir antes que mostrar menos de los pedidos.
  if (elegidos.length < cuantos) {
    for (const d of candidatos) {
      if (!d || !d.slug || elegidos.includes(d)) continue;
      elegidos.push(d);
      if (elegidos.length === cuantos) break;
    }
  }
  return elegidos;
}

export const COLOR_REGION: Record<string, string> = {
  GBA: '#1A2B48',
  Pampeana: '#2D4A7A',
  NOA: '#D4AF37',
  NEA: '#C08A2E',
  Cuyo: '#0F766E',
  Patagonia: '#3B82F6',
};

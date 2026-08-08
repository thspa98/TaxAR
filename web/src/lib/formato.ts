/**
 * formato.ts — Cómo se escribe un número en el sitio.
 *
 * Toda cifra pasa por acá. Es lo que evita que la misma cantidad aparezca
 * como "7596554", "7.596.554" y "7,6 M" en tres páginas distintas.
 *
 * Criterio: separador de miles con punto y decimales con coma, como se
 * escribe en Argentina.
 */

const ES = 'es-AR';

/** 7596554.2 -> "7.596.554" */
export function num(v: number | null | undefined, dec = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return 'sin dato';
  return v.toLocaleString(ES, { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

/** Millones de pesos -> la escala más legible para un lector no técnico. */
export function millones(v: number | null | undefined): string {
  if (v === null || v === undefined) return 'sin dato';
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${num(v / 1_000_000, 2)} billones`;
  if (abs >= 1_000) return `${num(v / 1_000, 1)} mil millones`;
  return `${num(v, 0)} millones`;
}

/** Pesos exactos, para el gasto por habitante. */
export function pesos(v: number | null | undefined): string {
  if (v === null || v === undefined) return 'sin dato';
  return `$${num(v, 0)}`;
}

/**
 * Alícuotas: 5 se escribe "5", 3,5 se escribe "3,5".
 *
 * Redondear a entero acá es un error grave y silencioso: convierte una
 * alícuota de 3,5% en "4%" y una de 1,8% en "2%". Los porcentajes chicos no
 * toleran el redondeo que sí toleran los millones de pesos.
 */
export function alicuota(v: number | null | undefined): string {
  if (v === null || v === undefined) return 'sin dato';
  return num(v, Number.isInteger(v) ? 0 : Math.min(2, (String(v).split('.')[1] ?? '').length));
}

export function pct(v: number | null | undefined, dec = 1): string {
  if (v === null || v === undefined) return 'sin dato';
  return `${num(v, dec)}%`;
}

/** Con signo explícito: un superávit tiene que verse distinto de un déficit. */
export function conSigno(v: number | null | undefined, dec = 0): string {
  if (v === null || v === undefined) return 'sin dato';
  return `${v > 0 ? '+' : ''}${num(v, dec)}`;
}

/** "1.383.357 millones de déficit" se entiende; "-1383357" no. */
export function resultado(v: number | null | undefined): { texto: string; tipo: 'superavit' | 'deficit' | 'sin-dato' } {
  if (v === null || v === undefined) return { texto: 'sin dato', tipo: 'sin-dato' };
  const tipo = v >= 0 ? 'superavit' : 'deficit';
  return { texto: `${millones(Math.abs(v))} de ${tipo === 'superavit' ? 'superávit' : 'déficit'}`, tipo };
}

/** "4,3 veces más" — la forma en que la gente compara de verdad. */
export function veces(a: number, b: number, dec = 1): string {
  if (!b) return 'sin dato';
  return num(a / b, dec);
}

export function fecha(iso: string): string {
  return new Date(iso).toLocaleDateString(ES, { day: 'numeric', month: 'long', year: 'numeric' });
}

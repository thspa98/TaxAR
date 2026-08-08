/**
 * Composicion.jsx — De dónde sale la plata y en qué se va.
 *
 * Dos columnas enfrentadas en vez de una torta: con 8 categorías, una torta
 * es ilegible y no se pueden comparar dos porciones parecidas. Las barras
 * ordenadas de mayor a menor se leen de un vistazo y se pueden comparar entre
 * provincias sin esfuerzo.
 *
 * Incluye una fila "Otros" con el residuo, para que las partes sumen el total
 * declarado por la fuente y no parezca que falta plata.
 */
import { useMemo, useState } from 'react';

const fmt = (v, dec = 0) =>
  v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

const monto = (v) => {
  if (Math.abs(v) >= 1_000_000) return `${fmt(v / 1_000_000, 2)} bill.`;
  if (Math.abs(v) >= 1000) return `${fmt(v / 1000, 1)} mil M`;
  return `${fmt(v)} M`;
};

function Columna({ titulo, items, total, resumen }) {
  const [abierto, setAbierto] = useState(null);
  return (
    <div className="col">
      <h3 className="col-tit">{titulo}</h3>
      <p className="col-total">{monto(total)}</p>
      <p className="col-res">{resumen}</p>

      <ul className="items">
        {items.map((it) => {
          const p = (it.valor / total) * 100;
          const on = abierto === it.slug;
          return (
            <li key={it.slug}>
              <button
                onClick={() => setAbierto(on ? null : it.slug)}
                aria-expanded={on}
                className={on ? 'fila on' : 'fila'}
              >
                <span className="pto" style={{ background: it.color }} />
                <span className="nom">{it.etiqueta}</span>
                <span className="pc">{fmt(p, 1)}%</span>
                <span className="mto">{monto(it.valor)}</span>
                <span className="track">
                  <span style={{ width: `${p}%`, background: it.color }} />
                </span>
              </button>
              {on && it.explica && <p className="expl">{it.explica}</p>}
            </li>
          );
        })}
      </ul>

      <style>{`
        .col-tit { font-size: .74rem; font-weight: 700; letter-spacing: .09em;
                   text-transform: uppercase; color: #64748B; margin-bottom: 4px; }
        .col-total { font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
                     font-size: 2rem; line-height: 1; color: #1A2B48;
                     font-variant-numeric: tabular-nums; }
        .col-res { font-size: .84rem; color: #64748B; margin: 6px 0 14px; line-height: 1.5; }
        .items { list-style: none; }
        .fila { width: 100%; background: none; border: 0; padding: 8px 0 9px; cursor: pointer;
                display: grid; grid-template-columns: 11px 1fr auto auto; gap: 4px 9px;
                align-items: center; text-align: left; font-family: inherit;
                border-bottom: 1px solid #EAEFF7; }
        .fila:hover .nom { color: #1A2B48; }
        .fila.on .nom { color: #1A2B48; font-weight: 600; }
        .pto { width: 11px; height: 11px; border-radius: 3px; }
        .nom { font-size: .88rem; color: #334155; }
        .pc  { font-size: .88rem; font-weight: 700; color: #1A2B48;
               font-variant-numeric: tabular-nums; }
        .mto { font-size: .76rem; color: #94A3B8; font-variant-numeric: tabular-nums;
               min-width: 66px; text-align: right; }
        .track { grid-column: 2 / -1; height: 5px; border-radius: 3px;
                 background: #EAEFF7; overflow: hidden; }
        .track > span { display: block; height: 100%; border-radius: 3px; }
        .expl { font-size: .83rem; color: #64748B; line-height: 1.6;
                padding: 9px 12px 11px 20px; background: #F7F9FC;
                border-radius: 0 0 8px 8px; margin-bottom: 4px; }
      `}</style>
    </div>
  );
}

export default function Composicion({
  categoriasPorAnio,   // { "2024": { slug: monto } }
  totalesPorAnio,      // { "2024": { ingresos, gastos } }
  glosario,            // { slug: {etiqueta, explica, bloque, color} }
  anios,
  anioInicial,
}) {
  const [anio, setAnio] = useState(String(anioInicial));

  const { ingresos, gastos, tIng, tGas } = useMemo(() => {
    const c = categoriasPorAnio[anio] ?? {};
    const t = totalesPorAnio[anio] ?? {};
    const arma = (bloque, total) => {
      const items = Object.entries(c)
        .filter(([k]) => glosario[k]?.bloque === bloque)
        .map(([k, v]) => ({ slug: k, valor: v, ...glosario[k] }))
        .filter((x) => x.valor > 0)
        .sort((a, b) => b.valor - a.valor);
      const resto = total - items.reduce((s, x) => s + x.valor, 0);
      if (resto > total * 0.005) {
        items.push({
          slug: '__otros__', valor: resto, etiqueta: 'Otros', color: '#CBD5E1',
          explica: bloque === 'gasto'
            ? 'Sobre todo intereses de la deuda e inversión financiera, que la fuente no abre por categoría.'
            : 'Ingresos de capital y partidas menores que la fuente no abre por categoría.',
        });
      }
      return items;
    };
    return {
      ingresos: arma('ingreso', t.ingresos ?? 0),
      gastos: arma('gasto', t.gastos ?? 0),
      tIng: t.ingresos ?? 0,
      tGas: t.gastos ?? 0,
    };
  }, [categoriasPorAnio, totalesPorAnio, glosario, anio]);

  const top = (arr) => (arr[0] ? `${arr[0].etiqueta} es lo más grande: ${fmt((arr[0].valor / (arr === ingresos ? tIng : tGas)) * 100, 0)}% del total.` : '');

  return (
    <div>
      <label className="sel">
        <span>Año</span>
        <select value={anio} onChange={(e) => setAnio(e.target.value)}>
          {anios.map((a) => <option key={a} value={String(a)}>{a}</option>)}
        </select>
      </label>

      <div className="dos">
        <Columna titulo="De dónde sale la plata" items={ingresos} total={tIng} resumen={top(ingresos)} />
        <Columna titulo="En qué se va" items={gastos} total={tGas} resumen={top(gastos)} />
      </div>

      <p className="ayuda">Tocá cualquier fila para ver qué incluye.</p>

      <style>{`
        .sel { display: inline-flex; align-items: center; gap: 9px; margin-bottom: 20px; }
        .sel span { font-size: .7rem; font-weight: 700; letter-spacing: .09em;
                    text-transform: uppercase; color: #64748B; }
        .sel select { font-family: inherit; font-size: .92rem; font-weight: 600;
                      padding: 7px 13px; border-radius: 9px; border: 1px solid #C9D3E5;
                      background: #fff; color: #1A2B48; cursor: pointer; }
        .sel select:hover { border-color: #D4AF37; }
        .dos { display: grid; grid-template-columns: 1fr 1fr; gap: 34px; }
        .ayuda { font-size: .79rem; color: #94A3B8; margin-top: 14px; }
        @media (max-width: 760px) { .dos { grid-template-columns: 1fr; gap: 30px; } }
      `}</style>
    </div>
  );
}

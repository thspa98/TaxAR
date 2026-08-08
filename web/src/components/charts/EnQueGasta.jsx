/**
 * EnQueGasta.jsx — La pregunta que de verdad importa.
 *
 * El resto del sitio responde "cuánto gasta cada provincia". Esto responde
 * en qué. Se muestra en dos niveles, igual que la fuente:
 *
 *   1. Una barra apilada con las cinco finalidades. Se lee de un vistazo qué
 *      proporción del presupuesto va a lo social y qué proporción a sostener
 *      la propia estructura del Estado.
 *   2. Adentro de "Servicios sociales", las nueve funciones ordenadas de mayor
 *      a menor: Educación, Salud, Jubilaciones, y el resto.
 *
 * Dos formas de leerlo. En porcentaje se compara una provincia chica con una
 * grande. En pesos por habitante se ve cuánto recibe efectivamente cada
 * persona, que es lo que se siente al ir a un hospital.
 */
import { useMemo, useState } from 'react';

const fmt = (v, dec = 0) =>
  v === null || v === undefined
    ? '—'
    : v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

const monto = (v) => {
  if (v == null) return '—';
  if (Math.abs(v) >= 1_000_000) return `${fmt(v / 1_000_000, 2)} bill.`;
  return `${fmt(v / 1000, 1)} mil M`;
};

export default function EnQueGasta({
  serie, finalidades, funciones, anios, anioInicial, aniosEstimados, notaEstimados,
}) {
  const [anio, setAnio] = useState(String(anioInicial));
  const [modo, setModo] = useState('pct');
  const [abierto, setAbierto] = useState(null);

  const f = useMemo(
    () => serie.find((x) => String(x.anio) === anio),
    [serie, anio],
  );

  if (!f) return <p style={{ color: '#64748B' }}>Sin datos de {anio}.</p>;

  const sufijo = modo === 'pct' ? '_pct' : '_hab';
  const val = (k) => f[`${k}${sufijo}`];
  const bruto = (k) => f[k];

  const fin = Object.entries(finalidades)
    .map(([k, m]) => ({ k, ...m, v: f[`${k}_pct`] ?? 0, dato: val(k), monto: bruto(k) }))
    .filter((x) => x.v > 0);

  const fun = Object.entries(funciones)
    .map(([k, m]) => ({ k, ...m, dato: val(k), monto: bruto(k), pct: f[`${k}_pct`] ?? 0 }))
    .filter((x) => x.monto > 0)
    .sort((a, b) => b.monto - a.monto);

  const maxFun = Math.max(...fun.map((x) => x.monto), 1);
  const estimado = aniosEstimados.includes(Number(anio));
  const muestra = (x) => (modo === 'pct' ? `${fmt(x.dato, 1)}%` : `$${fmt(x.dato)}`);

  return (
    <div>
      <div className="eq-ctrl">
        <label>
          <span>Año</span>
          <select value={anio} onChange={(e) => { setAnio(e.target.value); setAbierto(null); }}>
            {[...anios].reverse().map((a) => (
              <option key={a} value={String(a)}>{a}{aniosEstimados.includes(a) ? ' (estimado)' : ''}</option>
            ))}
          </select>
        </label>

        <div className="eq-modos" role="tablist">
          {[['pct', 'Del presupuesto'], ['hab', 'Por habitante']].map(([v, t]) => (
            <button key={v} role="tab" aria-selected={modo === v}
                    className={modo === v ? 'on' : ''}
                    onClick={() => setModo(v)}>{t}</button>
          ))}
        </div>

        <p className="eq-total">Gasto total {monto(f.total)}</p>
      </div>

      {estimado && (
        <p className="eq-aviso">
          <strong>Ojo con {anio}.</strong> {notaEstimados}
        </p>
      )}

      {/* --- nivel 1: las cinco finalidades --- */}
      <p className="eq-lbl">En qué se divide el presupuesto</p>
      <div className="eq-apilada" role="img"
           aria-label={`Reparto del presupuesto en ${anio} entre ${fin.map((x) => `${x.etiqueta} ${fmt(x.v, 1)}%`).join(', ')}`}>
        {fin.map((x) => (
          <button key={x.k}
                  className={abierto === x.k ? 'eq-tramo on' : 'eq-tramo'}
                  style={{ width: `${x.v}%`, background: x.color }}
                  onClick={() => setAbierto(abierto === x.k ? null : x.k)}
                  title={`${x.etiqueta}: ${muestra(x)}`}>
            {x.v > 7 && <span>{fmt(x.v, 0)}%</span>}
          </button>
        ))}
      </div>

      <ul className="eq-leyenda">
        {fin.map((x) => (
          <li key={x.k}>
            <button onClick={() => setAbierto(abierto === x.k ? null : x.k)}
                    className={abierto === x.k ? 'on' : ''}>
              <i style={{ background: x.color }} />
              <span className="eq-nom">{x.etiqueta}</span>
              <b>{muestra(x)}</b>
            </button>
          </li>
        ))}
      </ul>

      {abierto && (
        <p className="eq-expl">{finalidades[abierto].explica}</p>
      )}

      {/* --- nivel 2: las funciones sociales --- */}
      <p className="eq-lbl eq-lbl2">
        Adentro de Servicios sociales
        <span> — es el {fmt(f.social_pct, 0)}% del presupuesto</span>
      </p>

      <ul className="eq-func">
        {fun.map((x) => (
          <li key={x.k}>
            <button onClick={() => setAbierto(abierto === x.k ? null : x.k)}
                    className={abierto === x.k ? 'on' : ''}>
              <span className="eq-f-nom">{x.etiqueta}</span>
              <span className="eq-f-val">{muestra(x)}</span>
              <span className="eq-f-mto">{monto(x.monto)}</span>
              <span className="eq-track">
                <span style={{ width: `${(x.monto / maxFun) * 100}%`, background: x.color }} />
              </span>
            </button>
            {abierto === x.k && <p className="eq-expl eq-expl-f">{x.explica}</p>}
          </li>
        ))}
      </ul>

      <p className="eq-ayuda">Tocá cualquier rubro para ver qué incluye.</p>

      <style>{`
        .eq-ctrl { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 16px; margin-bottom: 18px; }
        .eq-ctrl label { display: flex; flex-direction: column; gap: 5px; }
        .eq-ctrl label span { font-size: .7rem; font-weight: 700; letter-spacing: .09em;
                              text-transform: uppercase; color: #64748B; }
        .eq-ctrl select { font-family: inherit; font-size: .92rem; font-weight: 600;
                          padding: 8px 13px; border-radius: 9px; border: 1px solid #C9D3E5;
                          background: #fff; color: #1A2B48; cursor: pointer; }
        .eq-ctrl select:hover { border-color: #D4AF37; }
        .eq-modos { display: flex; gap: 5px; }
        .eq-modos button { font-family: inherit; font-size: .84rem; font-weight: 600;
                           padding: 8px 14px; border-radius: 999px; cursor: pointer;
                           border: 1px solid #C9D3E5; background: #fff; color: #64748B; }
        .eq-modos button:hover { border-color: #D4AF37; color: #1A2B48; }
        .eq-modos button.on { background: #1A2B48; border-color: #1A2B48; color: #fff; }
        .eq-total { margin-left: auto; font-size: .87rem; color: #64748B; }

        .eq-aviso { background: rgba(180,83,9,.07); border: 1px solid rgba(180,83,9,.26);
                    border-left: 4px solid #B45309; border-radius: 10px;
                    padding: 12px 15px; margin-bottom: 16px; font-size: .87rem; line-height: 1.6; }
        .eq-aviso strong { color: #B45309; }

        .eq-lbl { font-size: .7rem; font-weight: 700; letter-spacing: .09em;
                  text-transform: uppercase; color: #64748B; margin-bottom: 9px; }
        .eq-lbl2 { margin-top: 30px; }
        .eq-lbl2 span { text-transform: none; letter-spacing: normal; font-weight: 400; }

        .eq-apilada { display: flex; height: 46px; border-radius: 9px; overflow: hidden; gap: 2px; }
        .eq-tramo { border: 0; cursor: pointer; padding: 0; position: relative;
                    transition: filter .15s ease; color: #fff; font-family: inherit;
                    font-size: .82rem; font-weight: 700; }
        .eq-tramo:hover { filter: brightness(1.2); }
        .eq-tramo.on { filter: brightness(1.3); box-shadow: inset 0 0 0 2px #fff; }

        .eq-leyenda { list-style: none; display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
        .eq-leyenda button {
          display: flex; align-items: center; gap: 8px; cursor: pointer;
          background: none; border: 1px solid transparent; border-radius: 8px;
          padding: 6px 10px; font-family: inherit; font-size: .85rem; color: #334155;
        }
        .eq-leyenda button:hover, .eq-leyenda button.on { border-color: #DDE3EE; background: #F7F9FC; }
        .eq-leyenda i { width: 11px; height: 11px; border-radius: 3px; flex: none; }
        .eq-leyenda b { color: #1A2B48; font-variant-numeric: tabular-nums; }

        .eq-expl { font-size: .89rem; color: #64748B; line-height: 1.62;
                   background: #F7F9FC; border-radius: 10px; padding: 12px 15px; margin-top: 12px; }
        .eq-expl-f { margin: 2px 0 8px 0; }

        .eq-func { list-style: none; margin-top: 10px; }
        .eq-func > li { border-bottom: 1px solid #EAEFF7; }
        .eq-func > li:last-child { border-bottom: 0; }
        .eq-func button {
          width: 100%; background: none; border: 0; cursor: pointer; font-family: inherit;
          display: grid; grid-template-columns: 1fr auto auto; gap: 4px 12px;
          align-items: center; text-align: left; padding: 10px 0;
        }
        .eq-func button:hover .eq-f-nom, .eq-func button.on .eq-f-nom { color: #1A2B48; }
        .eq-f-nom { font-size: .9rem; color: #334155; }
        .eq-f-val { font-size: .9rem; font-weight: 700; color: #1A2B48;
                    font-variant-numeric: tabular-nums; }
        .eq-f-mto { font-size: .77rem; color: #94A3B8; font-variant-numeric: tabular-nums;
                    min-width: 74px; text-align: right; }
        .eq-track { grid-column: 1 / -1; height: 6px; border-radius: 3px;
                    background: #EAEFF7; overflow: hidden; }
        .eq-track > span { display: block; height: 100%; border-radius: 3px; }

        .eq-ayuda { font-size: .79rem; color: #94A3B8; margin-top: 14px; }

        @media (max-width: 620px) {
          .eq-total { margin-left: 0; width: 100%; }
          .eq-f-mto { display: none; }
        }
      `}</style>
    </div>
  );
}

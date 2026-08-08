/**
 * MapaArgentina.jsx — El mapa como forma de entrar a los datos.
 *
 * Mucha gente no sabe en qué puesto está su provincia, pero sí sabe dónde
 * queda. El mapa convierte "buscar" en "señalar".
 *
 * Decisión de color: todas las provincias van del mismo tono y el amarillo se
 * reserva para lo que el usuario está tocando o eligió. Pintar cada provincia
 * de un color distinto según el dato hacía que los límites se perdieran y que
 * el mapa compitiera con el ranking, que para comparar magnitudes funciona
 * mejor. Acá el trabajo del mapa es la ubicación; los números están al lado.
 *
 * Dos modos:
 *   'explorar' — al hacer clic se abre la ficha de la provincia.
 *   'comparar' — se eligen dos cualesquiera y aparece la tabla enfrentada.
 */
import { useMemo, useState } from 'react';

const C = {
  base: '#43608F',      // el mismo para las 24
  borde: '#FFFFFF',
  activa: '#F0C338',    // amarillo: lo que el mouse está tocando
  elegida: '#D4AF37',   // oro: lo que el usuario seleccionó
  bordeElegida: '#8A6D12',
  sinDato: 'url(#rayado)',
};

const fmt = (v, dec = 0) =>
  v === null || v === undefined
    ? 'sin dato'
    : v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

const monto = (v) => {
  if (v === null || v === undefined) return 'sin dato';
  if (Math.abs(v) >= 1_000_000) return `${fmt(v / 1_000_000, 2)} bill.`;
  return `${fmt(v / 1000, 1)} mil M`;
};

const FILAS = [
  ['Habitantes', 'poblacion', (v) => fmt(v)],
  ['Gasto total', 'gastos_totales', monto],
  ['Gasto por habitante', 'gasto_per_capita', (v) => `$${fmt(v)}`],
  ['Impuestos por habitante', 'impuestos_por_habitante', (v) => `$${fmt(v)}`],
  ['Depende de la Nación', 'dependencia_nacion', (v) => `${fmt(v, 1)}%`],
  ['Resultado sobre ingresos', 'resultado_sobre_ingresos', (v) => `${v >= 0 ? '+' : ''}${fmt(v, 1)}%`],
];

export default function MapaArgentina({
  viewBox, formas, datos, anio, anios, atribucion,
}) {
  const [anioSel, setAnioSel] = useState(String(anio));
  const [modo, setModo] = useState('explorar');
  const [sel, setSel] = useState([]);
  const [hover, setHover] = useState(null);

  const delAnio = datos[anioSel] ?? {};
  const sinDato = useMemo(
    () => Object.keys(formas).filter((s) => !delAnio[s]),
    [formas, delAnio],
  );

  function clic(slug) {
    if (!delAnio[slug]) return;
    if (modo === 'explorar') {
      window.location.href = `/provincia/${slug}/`;
      return;
    }
    setSel((s) =>
      s.includes(slug) ? s.filter((x) => x !== slug) : s.length < 2 ? [...s, slug] : [s[1], slug]);
  }

  const activo = hover ? delAnio[hover] : null;
  const [a, b] = sel.map((s) => delAnio[s] ?? null);
  const listo = sel.length === 2 && a && b;

  return (
    <div>
      <div className="ctrl">
        <div className="modos" role="tablist">
          {[['explorar', 'Explorar'], ['comparar', 'Comparar dos']].map(([v, t]) => (
            <button key={v} role="tab" aria-selected={modo === v}
                    className={modo === v ? 'on' : ''}
                    onClick={() => { setModo(v); setSel([]); }}>{t}</button>
          ))}
        </div>

        <label>
          <span>Año</span>
          <select value={anioSel} onChange={(e) => { setAnioSel(e.target.value); setSel([]); }}>
            {anios.map((y) => <option key={y} value={String(y)}>{y}</option>)}
          </select>
        </label>

        <p className="pista">
          {modo === 'explorar'
            ? 'Tocá una provincia para abrir su ficha.'
            : sel.length === 0 ? 'Elegí dos provincias, las que quieras.'
            : sel.length === 1 ? `${delAnio[sel[0]]?.nombre}. Falta una más.`
            : 'Listo — la comparación está abajo.'}
          {sel.length > 0 && (
            <button className="limpiar" onClick={() => setSel([])}>Empezar de nuevo</button>
          )}
        </p>
      </div>

      <div className="lienzo">
        <svg viewBox={viewBox} className="mapa" role="img"
             aria-label={`Mapa de las 24 jurisdicciones argentinas. Tocá una para ver sus datos de ${anioSel}.`}>
          <defs>
            <pattern id="rayado" patternUnits="userSpaceOnUse" width="7" height="7"
                     patternTransform="rotate(45)">
              <rect width="7" height="7" fill="#E7ECF4" />
              <line x1="0" y1="0" x2="0" y2="7" stroke="#B9C6DC" strokeWidth="2.5" />
            </pattern>
          </defs>

          {Object.entries(formas).map(([slug, d]) => {
            const hay = !!delAnio[slug];
            const elegida = sel.includes(slug);
            const tocada = hover === slug;
            return (
              <path
                key={slug}
                d={d}
                fill={!hay ? C.sinDato : elegida ? C.elegida : tocada ? C.activa : C.base}
                stroke={elegida ? C.bordeElegida : C.borde}
                strokeWidth={elegida ? 2.2 : 1.1}
                className={`prov ${hay ? '' : 'sin'}`}
                tabIndex={hay ? 0 : -1}
                role={hay ? 'button' : 'presentation'}
                aria-label={hay
                  ? `${delAnio[slug].nombre}: $${fmt(delAnio[slug].gasto_per_capita)} de gasto por habitante`
                  : undefined}
                onMouseEnter={() => setHover(slug)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(slug)}
                onBlur={() => setHover(null)}
                onClick={() => clic(slug)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); clic(slug); }
                }}
              />
            );
          })}
        </svg>

        <div className="panel">
          {activo ? (
            <>
              <p className="p-nom">{activo.nombre}</p>
              <p className="p-val">${fmt(activo.gasto_per_capita)}</p>
              <p className="p-sub">de gasto por habitante en {anioSel}</p>
              <dl className="p-lista">
                {FILAS.slice(0, 5).map(([txt, k, f]) => (
                  <div key={k}>
                    <dt>{txt}</dt>
                    <dd>{activo[k] === null || activo[k] === undefined ? '—' : f(activo[k])}</dd>
                  </div>
                ))}
              </dl>
              <p className="p-ir">
                {modo === 'explorar' ? 'Tocá para ver la ficha completa' : 'Tocá para elegirla'}
              </p>
            </>
          ) : hover && sinDato.includes(hover) ? (
            <>
              <p className="p-nom">Sin dato</p>
              <p className="p-sin">No reportó {anioSel}</p>
              <p className="p-sub">Elegí un año anterior para verla.</p>
            </>
          ) : (
            <>
              <p className="p-tit">Las 24 jurisdicciones</p>
              <p className="p-ayuda-grande">
                Pasá el mouse por cualquier provincia y sus números aparecen acá.
              </p>
              <ul className="ref">
                <li><i style={{ background: C.base }} />Con datos de {anioSel}</li>
                <li><i style={{ background: C.activa }} />La que estás tocando</li>
                {sinDato.length > 0 && <li><i className="ref-rayado" />No reportó {anioSel}</li>}
              </ul>
            </>
          )}
        </div>
      </div>

      {listo && (
        <div className="comparacion">
          <h3 className="c-tit">{a.nombre} <span>vs</span> {b.nombre}</h3>
          <table>
            <thead>
              <tr><th></th><th>{a.corto}</th><th>{b.corto}</th><th>Diferencia</th></tr>
            </thead>
            <tbody>
              {FILAS.map(([txt, k, f]) => {
                const va = a[k], vb = b[k];
                const comparable = va != null && vb != null && va > 0 && vb > 0;
                const veces = comparable ? Math.max(va, vb) / Math.min(va, vb) : null;
                return (
                  <tr key={k} className={k === 'gasto_per_capita' ? 'destacar' : ''}>
                    <td>{txt}</td>
                    <td className={va > vb ? 'mayor' : ''}>{va == null ? '—' : f(va)}</td>
                    <td className={vb > va ? 'mayor' : ''}>{vb == null ? '—' : f(vb)}</td>
                    <td className="dif">
                      {veces == null ? '—' : veces > 1.02 ? `${fmt(veces, 1)}x` : 'casi igual'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="c-links">
            <a href={`/provincia/${sel[0]}/`}>Ficha de {a.corto}</a>
            <a href={`/provincia/${sel[1]}/`}>Ficha de {b.corto}</a>
          </p>
        </div>
      )}

      {atribucion && <p className="atrib">Contornos: {atribucion}</p>}

      <style>{`
        .ctrl { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 16px; margin-bottom: 16px; }
        .ctrl label { display: flex; flex-direction: column; gap: 5px; }
        .ctrl label span { font-size: .7rem; font-weight: 700; letter-spacing: .09em;
                           text-transform: uppercase; color: #64748B; }
        .ctrl select { font-family: inherit; font-size: .92rem; font-weight: 600;
                       padding: 8px 13px; border-radius: 9px; border: 1px solid #C9D3E5;
                       background: #fff; color: #1A2B48; cursor: pointer; }
        .ctrl select:hover { border-color: #D4AF37; }
        .modos { display: flex; gap: 5px; }
        .modos button { font-family: inherit; font-size: .86rem; font-weight: 600;
                        padding: 8px 15px; border-radius: 999px; cursor: pointer;
                        border: 1px solid #C9D3E5; background: #fff; color: #64748B; }
        .modos button:hover { border-color: #D4AF37; color: #1A2B48; }
        .modos button.on { background: #1A2B48; border-color: #1A2B48; color: #fff; }
        .pista { margin-left: auto; font-size: .86rem; color: #64748B;
                 display: flex; align-items: center; gap: 12px; }
        .limpiar { font-family: inherit; font-size: .8rem; font-weight: 600; cursor: pointer;
                   background: none; border: 0; color: #8A6D12; text-decoration: underline; }

        .lienzo { display: grid; grid-template-columns: 1fr 262px; gap: 24px; align-items: start; }
        .mapa { width: 100%; height: auto; max-height: 640px; display: block; }
        .prov { cursor: pointer; outline: none;
                transition: fill .13s ease, stroke-width .13s ease; }
        .prov.sin { cursor: default; }
        .prov:focus-visible { stroke: #8A6D12; stroke-width: 2.6; }

        .panel { background: #F7F9FC; border: 1px solid #DDE3EE; border-radius: 12px;
                 padding: 20px; position: sticky; top: 84px; min-height: 250px; }
        .p-tit, .p-nom { font-size: .74rem; font-weight: 700; letter-spacing: .08em;
                         text-transform: uppercase; color: #64748B; }
        .p-nom { color: #1A2B48; letter-spacing: .03em; font-size: .84rem; line-height: 1.3; }
        .p-val { font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
                 font-size: 2.2rem; line-height: 1.05; color: #1A2B48; margin-top: 6px;
                 font-variant-numeric: tabular-nums; }
        .p-sin { font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
                 font-size: 1.5rem; color: #B45309; margin-top: 6px; }
        .p-sub { font-size: .79rem; color: #94A3B8; margin-top: 3px; line-height: 1.45; }
        .p-lista { margin-top: 15px; border-top: 1px solid #E3E9F3; padding-top: 11px; }
        .p-lista > div { display: flex; justify-content: space-between; gap: 10px;
                         padding: 5px 0; font-size: .83rem; }
        .p-lista dt { color: #64748B; }
        .p-lista dd { font-weight: 600; color: #1E293B; font-variant-numeric: tabular-nums;
                      white-space: nowrap; }
        .p-ir { margin-top: 13px; font-size: .76rem; color: #8A6D12; font-weight: 600; }
        .p-ayuda-grande { font-size: .93rem; color: #64748B; margin-top: 10px; line-height: 1.6; }
        .ref { list-style: none; margin-top: 18px; border-top: 1px solid #E3E9F3; padding-top: 13px; }
        .ref li { display: flex; align-items: center; gap: 9px; padding: 4px 0;
                  font-size: .8rem; color: #64748B; }
        .ref i { width: 14px; height: 14px; border-radius: 4px; flex: none;
                 border: 1px solid rgba(26,43,72,.15); }
        .ref-rayado { background: repeating-linear-gradient(45deg, #E7ECF4 0 2px, #B9C6DC 2px 4px); }

        .comparacion { margin-top: 24px; border: 1px solid #DDE3EE; border-radius: 12px;
                       padding: 22px; background: #fff; }
        .c-tit { font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
                 font-size: 1.55rem; color: #1A2B48; margin-bottom: 15px; }
        .c-tit span { color: #94A3B8; font-weight: 700; }
        .comparacion table { width: 100%; border-collapse: collapse;
                             font-variant-numeric: tabular-nums; }
        .comparacion th { font-size: .72rem; font-weight: 700; letter-spacing: .07em;
                          text-transform: uppercase; color: #64748B; text-align: right;
                          padding: 8px; border-bottom: 2px solid #DDE3EE; }
        .comparacion th:first-child { text-align: left; }
        .comparacion td { padding: 10px 8px; border-bottom: 1px solid #EAEFF7;
                          text-align: right; font-size: .92rem; }
        .comparacion td:first-child { text-align: left; color: #64748B; }
        .comparacion .mayor { font-weight: 700; color: #1A2B48; }
        .comparacion .dif { color: #8A6D12; font-weight: 600; }
        .comparacion tr.destacar { background: rgba(212,175,55,.1); }
        .c-links { display: flex; gap: 18px; margin-top: 15px; font-size: .88rem; font-weight: 600; }
        .atrib { font-size: .74rem; color: #94A3B8; margin-top: 13px; }

        @media (max-width: 820px) {
          .lienzo { grid-template-columns: 1fr; }
          .panel { position: static; min-height: 0; }
          .mapa { max-height: 440px; margin-inline: auto; }
          .pista { margin-left: 0; width: 100%; }
        }
      `}</style>
    </div>
  );
}

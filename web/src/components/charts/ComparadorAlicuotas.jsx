/**
 * ComparadorAlicuotas.jsx — Las alícuotas de las 24, y un comparador con mapa.
 *
 * Arranca con la tabla completa, ordenable. Al tocar "Comparar dos" aparece el
 * mapa, se eligen dos jurisdicciones y quedan enfrentadas.
 *
 * Casi todas las alícuotas son rangos, no números fijos: cada provincia cobra
 * distinto según el nivel de facturación, la actividad y si el contribuyente
 * está radicado ahí. Mostrar sólo el mínimo o sólo el máximo sería más prolijo
 * y más falso, así que se muestran los dos y se ordena por el máximo, que es
 * el que le toca a la mayoría del comercio grande.
 */
import { useEffect, useMemo, useRef, useState } from 'react';

const C = {
  base: '#43608F',
  borde: '#FFFFFF',
  activa: '#F0C338',
  elegida: '#D4AF37',
  bordeElegida: '#8A6D12',
};

const n = (v) => v.toLocaleString('es-AR', { maximumFractionDigits: 2 });
const rango = (a) => (a == null ? '—' : a.rango ? `${n(a.min)}% a ${n(a.max)}%` : `${n(a.min)}%`);

export default function ComparadorAlicuotas({
  datos, impuestos, orden, jurisdicciones, indecASlug, atribucion,
}) {
  // El mapa del IGN es un componente vanilla; acá sólo se lo crea, se traduce
  // su callback de código INDEC a slug, y se lo destruye al salir.
  const cajaRef = useRef(null);
  const instRef = useRef(null);
  const [comparando, setComparando] = useState(false);
  const [sel, setSel] = useState([]);
  const [hover, setHover] = useState(null);
  const [ordenCol, setOrdenCol] = useState({ col: 'nombre', desc: false });

  const filas = useMemo(() => {
    const arr = Object.entries(datos).map(([slug, a]) => ({
      slug, nombre: jurisdicciones[slug].nombre, corto: jurisdicciones[slug].corto, a,
    }));
    const { col, desc } = ordenCol;
    arr.sort((x, y) => {
      if (col === 'nombre') {
        return desc ? y.nombre.localeCompare(x.nombre, 'es') : x.nombre.localeCompare(y.nombre, 'es');
      }
      const vx = x.a[col]?.max ?? -1, vy = y.a[col]?.max ?? -1;
      return desc ? vy - vx : vx - vy;
    });
    return arr;
  }, [datos, jurisdicciones, ordenCol]);

  const ordenar = (col) =>
    setOrdenCol((o) => ({ col, desc: o.col === col ? !o.desc : col !== 'nombre' }));

  function clic(slug) {
    if (!datos[slug]) return;
    setSel((s) =>
      s.includes(slug) ? s.filter((x) => x !== slug) : s.length < 2 ? [...s, slug] : [s[1], slug]);
  }

  useEffect(() => {
    if (!comparando) { instRef.current?.destruir(); instRef.current = null; return; }
    let cancelado = false;
    const arrancar = () => {
      if (cancelado || !cajaRef.current || !window.MapaArgentina) return;
      instRef.current = window.MapaArgentina.crear({
        el: cajaRef.current,
        maxSeleccion: 2,
        vista: 'continental',
        onHover: (p) => setHover(p ? indecASlug[p.indec] ?? null : null),
        onChange: (s) => setSel(s.map((p) => indecASlug[p.indec]).filter(Boolean)),
      });
    };
    if (window.MapaArgentina) arrancar();
    else {
      const t = setInterval(() => { if (window.MapaArgentina) { clearInterval(t); arrancar(); } }, 60);
      setTimeout(() => clearInterval(t), 10000);
      return () => { cancelado = true; clearInterval(t); instRef.current?.destruir(); };
    }
    return () => { cancelado = true; instRef.current?.destruir(); };
  }, [comparando]);

  const [a, b] = sel.map((s) => (datos[s] ? { slug: s, ...jurisdicciones[s], a: datos[s] } : null));
  const listo = sel.length === 2 && a && b;

  return (
    <div>
      {/* El comparador va en su propio recuadro, separado de la tabla: es una
          acción, no una fila más de datos. */}
      <div className="ca-accion">
        <div className="ca-accion-txt">
          <p className="ca-accion-tit">
            {comparando ? 'Comparando dos provincias' : '¿Querés comparar dos provincias?'}
          </p>
          <p className="ca-accion-sub">
            {!comparando && 'Elegilas en el mapa y sus alícuotas quedan enfrentadas.'}
            {comparando && sel.length === 0 && 'Tocá dos provincias en el mapa.'}
            {comparando && sel.length === 1 && `${a?.nombre} elegida. Falta una más.`}
            {comparando && sel.length === 2 && `${a?.nombre} y ${b?.nombre}. Mirá la tabla de la derecha.`}
          </p>
        </div>

        <div className="ca-accion-btns">
          {comparando && sel.length > 0 && (
            <button className="ca-limpiar" onClick={() => { setSel([]); instRef.current?.limpiar(); }}>Empezar de nuevo</button>
          )}
          <button className={comparando ? 'ca-cta ca-on' : 'ca-cta'}
                  onClick={() => { setComparando(!comparando); setSel([]); }}>
            {comparando ? 'Cerrar el mapa' : 'Comparar en el mapa'}
          </button>
        </div>
      </div>

      {comparando ? (
        <div className="ca-lienzo">
          <div className="ca-mapa-caja" ref={cajaRef} />

          <div className="ca-panel">
            {listo ? (
              <>
                <h3 className="ca-c-tit">{a.corto} <span>vs</span> {b.corto}</h3>
                <table className="ca-comp">
                  <tbody>
                    {orden.map((k) => {
                      const va = a.a[k], vb = b.a[k];
                      const may = va && vb ? (va.max > vb.max ? 'a' : vb.max > va.max ? 'b' : null) : null;
                      return (
                        <tr key={k}>
                          <td className="ca-c-imp">{impuestos[k].corto}</td>
                          <td className={may === 'a' ? 'ca-mayor' : ''}>{rango(va)}</td>
                          <td className={may === 'b' ? 'ca-mayor' : ''}>{rango(vb)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <p className="ca-c-links">
                  <a href={`/provincia/${a.slug}/`}>Ficha de {a.corto}</a>
                  <a href={`/provincia/${b.slug}/`}>Ficha de {b.corto}</a>
                </p>
              </>
            ) : hover && datos[hover] ? (
              <>
                <p className="ca-p-nom">{jurisdicciones[hover].nombre}</p>
                <dl className="ca-p-lista">
                  {orden.map((k) => (
                    <div key={k}>
                      <dt>{impuestos[k].corto}</dt>
                      <dd>{rango(datos[hover][k])}</dd>
                    </div>
                  ))}
                </dl>
                <p className="ca-p-ir">Tocá para elegirla</p>
              </>
            ) : (
              <>
                <p className="ca-p-tit">Elegí dos</p>
                <p className="ca-p-ayuda">
                  Tocá una provincia y después otra. Sus alícuotas quedan enfrentadas acá.
                </p>
              </>
            )}
          </div>
        </div>
      ) : (
        <details className="ca-plegable">
          <summary>
            <span className="ca-pleg-txt">
              <span className="ca-pleg-tit">Ver las alícuotas de las 24 jurisdicciones</span>
              <span className="ca-pleg-nota">
                Tabla completa, ordenable por cualquier columna.
              </span>
            </span>
            <span className="ca-flecha" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none"
                   stroke="currentColor" strokeWidth="2.6"
                   strokeLinecap="round" strokeLinejoin="round">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </span>
          </summary>

          <div className="ca-scroll">
          <table className="ca-tabla-alic">
            <thead>
              <tr>
                <th>
                  <button onClick={() => ordenar('nombre')} className={ordenCol.col === 'nombre' ? 'ca-on' : ''}>
                    Jurisdicción{ordenCol.col === 'nombre' && <i>{ordenCol.desc ? '▾' : '▴'}</i>}
                  </button>
                </th>
                {orden.map((k) => (
                  <th key={k} className="ca-der">
                    <button onClick={() => ordenar(k)} className={ordenCol.col === k ? 'ca-on' : ''}>
                      {impuestos[k].corto}{ordenCol.col === k && <i>{ordenCol.desc ? '▾' : '▴'}</i>}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <tr key={f.slug}>
                  <td><a href={`/provincia/${f.slug}/`}>{f.nombre}</a></td>
                  {orden.map((k) => (
                    <td key={k} className="ca-der">{rango(f.a[k])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </details>
      )}

      {comparando && atribucion && <p className="ca-atrib">Contornos: {atribucion}</p>}

      <style>{`
        /* El comparador, en su propio recuadro. */
        .ca-accion {
          display: flex; flex-wrap: wrap; align-items: center;
          justify-content: space-between; gap: 16px;
          background: #F2F5FA; border: 1px solid #DDE3EE;
          border-left: 4px solid #3B5998;
          border-radius: 12px; padding: 17px 20px; margin-bottom: 18px;
        }
        .ca-accion-tit { font-weight: 700; color: #1A2B48; font-size: 1rem; }
        .ca-accion-sub { font-size: .87rem; color: #64748B; margin-top: 3px; line-height: 1.5; }
        .ca-accion-btns { display: flex; align-items: center; gap: 14px; }

        /* La tabla, plegada. */
        .ca-plegable { border: 1px solid #DDE3EE; border-radius: 12px; background: #fff; }
        .ca-plegable > summary {
          display: flex; align-items: center; justify-content: space-between;
          gap: 18px; padding: 17px 20px; cursor: pointer; list-style: none;
          border-radius: 12px; transition: background .15s ease;
        }
        .ca-plegable > summary::-webkit-details-marker { display: none; }
        .ca-plegable > summary:hover { background: rgba(59,89,152,.05); }
        .ca-plegable > summary:focus-visible { outline: 3px solid #D4AF37; outline-offset: -3px; }
        .ca-pleg-tit {
          display: block; font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
          font-size: 1.22rem; line-height: 1.15; color: #1A2B48;
        }
        .ca-pleg-nota { display: block; font-size: .84rem; color: #64748B; margin-top: 3px; }
        .ca-flecha {
          display: grid; place-items: center; flex: none;
          width: 34px; height: 34px; border-radius: 50%;
          background: #3B5998; color: #fff;
          transition: transform .25s cubic-bezier(.22,.8,.3,1), background .15s ease;
        }
        .ca-plegable > summary:hover .ca-flecha { background: #1A2B48; }
        .ca-plegable[open] .ca-flecha { transform: rotate(180deg); }
        .ca-plegable[open] > summary {
          border-bottom: 1px solid #DDE3EE; border-radius: 12px 12px 0 0;
        }
        .ca-plegable .ca-scroll { padding: 8px 20px 20px; }
        .ca-cta { font-family: inherit; font-size: .93rem; font-weight: 600; cursor: pointer;
               padding: 11px 22px; border-radius: 999px;
               background: #1A2B48; color: #fff; border: 1px solid #1A2B48;
               transition: background .16s ease, transform .16s ease; }
        .ca-cta:hover { background: #2D4A7A; transform: translateY(-1px); }
        .ca-cta.ca-on { background: #fff; color: #1A2B48; }
        .ca-pista { font-size: .87rem; color: #64748B; display: flex; align-items: center; gap: 12px; }
        .ca-limpiar { font-family: inherit; font-size: .8rem; font-weight: 600; cursor: pointer;
                   background: none; border: 0; color: #8A6D12; text-decoration: underline; }

        .ca-scroll { overflow-x: auto; }
        .ca-tabla-alic { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
        .ca-tabla-alic th { padding: 0 0 9px; border-bottom: 2px solid #DDE3EE; text-align: left; }
        .ca-tabla-alic th.ca-der { text-align: right; }
        .ca-tabla-alic th button { background: none; border: 0; cursor: pointer; font-family: inherit;
                                font-size: .71rem; font-weight: 700; letter-spacing: .07em;
                                text-transform: uppercase; color: #64748B; padding: 4px 6px;
                                border-radius: 6px; white-space: nowrap; }
        .ca-tabla-alic th.ca-der button { margin-left: auto; display: block; }
        .ca-tabla-alic th button:hover { color: #1A2B48; background: rgba(26,43,72,.06); }
        .ca-tabla-alic th button.ca-on { color: #1A2B48; }
        .ca-tabla-alic th i { font-style: normal; margin-left: 3px; }
        .ca-tabla-alic td { padding: 10px 8px; border-bottom: 1px solid #EAEFF7; font-size: .91rem; }
        .ca-tabla-alic td.ca-der { text-align: right; }
        .ca-tabla-alic tbody tr:hover { background: rgba(212,175,55,.08); }
        .ca-tabla-alic td a { font-weight: 600; color: #1A2B48; text-decoration: none; }
        .ca-tabla-alic tbody tr:hover td a { text-decoration: underline; text-decoration-color: #D4AF37; }

        .ca-lienzo { display: grid; grid-template-columns: 1fr 300px; gap: 24px; align-items: start; }
        .ca-mapa-caja {
          width: 100%; height: 520px; overflow: hidden;
          border-radius: 12px; background: #F7F9FC; border: 1px solid #DDE3EE;
          --mapar-fill: #43608F; --mapar-hover: #F0C338;
          --mapar-stroke: #ffffff; --mapar-stroke-w: 0.9;
          --mapar-sel-1: #1A2B48; --mapar-sel-2: #D4AF37;
        }
        .ca-prov { cursor: pointer; outline: none; transition: fill .13s ease; }
        .ca-prov:focus-visible { stroke: #8A6D12; stroke-width: 2.6; }

        .ca-panel { background: #F7F9FC; border: 1px solid #DDE3EE; border-radius: 12px;
                 padding: 20px; position: sticky; top: 84px; min-height: 230px; }
        .ca-p-tit, .ca-p-nom { font-size: .74rem; font-weight: 700; letter-spacing: .08em;
                         text-transform: uppercase; color: #64748B; }
        .ca-p-nom { color: #1A2B48; letter-spacing: .03em; font-size: .85rem; line-height: 1.3; }
        .ca-p-lista { margin-top: 13px; border-top: 1px solid #E3E9F3; padding-top: 11px; }
        .ca-p-lista > div { display: flex; justify-content: space-between; gap: 12px;
                         padding: 6px 0; font-size: .83rem; }
        .ca-p-lista dt { color: #64748B; }
        .ca-p-lista dd { font-weight: 600; color: #1E293B; white-space: nowrap;
                      font-variant-numeric: tabular-nums; }
        .ca-p-ir { margin-top: 12px; font-size: .76rem; color: #8A6D12; font-weight: 600; }
        .ca-p-ayuda { font-size: .92rem; color: #64748B; margin-top: 9px; line-height: 1.6; }

        .ca-c-tit { font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
                 font-size: 1.35rem; color: #1A2B48; margin-bottom: 12px; }
        .ca-c-tit span { color: #94A3B8; }
        .ca-comp { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
        .ca-comp td { padding: 9px 4px; border-bottom: 1px solid #E3E9F3;
                   font-size: .84rem; text-align: right; white-space: nowrap; }
        .ca-comp .ca-c-imp { text-align: left; color: #64748B; white-space: normal; padding-right: 8px; }
        .ca-comp .ca-mayor { font-weight: 700; color: #1A2B48; }
        .ca-c-links { display: flex; flex-direction: column; gap: 6px; margin-top: 14px;
                   font-size: .85rem; font-weight: 600; }
        .ca-atrib { font-size: .74rem; color: #94A3B8; margin-top: 13px; }

        @media (max-width: 820px) {
          .ca-lienzo { grid-template-columns: 1fr; }
          .ca-panel { position: static; }
          .ca-mapa-caja { height: 400px; }
        }
      `}</style>
    </div>
  );
}

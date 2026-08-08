/**
 * MapaIGN.jsx — El mapa oficial del Instituto Geográfico Nacional.
 *
 * Reemplaza al mapa anterior, que no incluía Malvinas, las islas del Atlántico
 * Sur ni el Sector Antártico. Este trae el territorio completo tal como lo
 * define el IGN, y por eso la provincia de Tierra del Fuego se resalta entera
 * —Isla Grande, Malvinas, Georgias, Sandwich y sector antártico— cuando se la
 * selecciona.
 *
 * Distinción importante que el sitio no puede borrar: **el mapa muestra el
 * territorio completo, los datos son continentales.** Lo que cada provincia
 * ejecuta y reporta es actividad continental; nadie mide gasto en la Antártida.
 * Esa aclaración va visible, no escondida en la metodología.
 *
 * El componente de abajo es JavaScript sin dependencias (`mapa-argentina.js`),
 * no React. Este archivo es sólo el puente: lo crea al montar, traduce sus
 * callbacks de código INDEC a los slugs del sitio, y lo destruye al salir.
 */
import { useEffect, useRef, useState } from 'react';

const fmt = (v, dec = 0) =>
  v === null || v === undefined
    ? '—'
    : v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

const monto = (v) => {
  if (v == null) return '—';
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

export default function MapaIGN({
  indecASlug, datos, anio, anios, atribucion, notaTerritorio, alto = 560,
}) {
  const cajaRef = useRef(null);
  const instRef = useRef(null);

  const [listo, setListo] = useState(false);
  const [error, setError] = useState(false);
  const [anioSel, setAnioSel] = useState(String(anio));
  const [modo, setModo] = useState('explorar');
  const [vista, setVista] = useState('continental');
  const [sel, setSel] = useState([]);
  const [hover, setHover] = useState(null);

  // Refs para que los callbacks del componente vanilla —que se registran una
  // sola vez— siempre lean el estado actual y no el del primer render.
  const modoRef = useRef(modo);
  const anioRef = useRef(anioSel);
  useEffect(() => { modoRef.current = modo; }, [modo]);
  useEffect(() => { anioRef.current = anioSel; }, [anioSel]);

  useEffect(() => {
    let cancelado = false;

    const arrancar = () => {
      if (cancelado || !cajaRef.current || !window.MapaArgentina) return;
      try {
      instRef.current = window.MapaArgentina.crear({
        el: cajaRef.current,
        maxSeleccion: 2,
        modo: 'cola',
        vista: 'continental',
        zoom: true,
        tooltip: true,
        onHover: (p) => setHover(p ? indecASlug[p.indec] ?? null : null),
        onChange: (seleccion) => {
          const slugs = seleccion.map((p) => indecASlug[p.indec]).filter(Boolean);

          // En modo explorar el click abre la ficha; el mapa nunca queda con
          // una selección colgada.
          if (modoRef.current === 'explorar') {
            const ultimo = slugs[slugs.length - 1];
            if (ultimo) {
              instRef.current?.limpiar();
              window.location.href = `/provincia/${ultimo}/`;
            }
            return;
          }
          setSel(slugs);
        },
      });
        setListo(true);
      } catch (e) {
        // Si el componente del mapa falla, el resto de la página tiene que
        // seguir funcionando. Sin este try, la excepción sube por el efecto y
        // React desmonta la isla entera.
        console.error('No se pudo crear el mapa:', e);
        setError(true);
      }
    };

    if (window.MapaArgentina) {
      arrancar();
    } else {
      // El script se carga con `defer`; puede no estar listo cuando la isla
      // hidrata. Se espera sin bloquear nada.
      const t = setInterval(() => {
        if (window.MapaArgentina) { clearInterval(t); arrancar(); }
      }, 60);
      setTimeout(() => clearInterval(t), 10000);
      return () => { cancelado = true; clearInterval(t); try { instRef.current?.destruir(); } catch {} };
    }

    return () => { cancelado = true; try { instRef.current?.destruir(); } catch {} };
  }, []);

  useEffect(() => { instRef.current?.setVista(vista); }, [vista]);

  const delAnio = datos[anioSel] ?? {};
  const activo = hover ? delAnio[hover] : null;
  const [a, b] = sel.map((s) => delAnio[s] ?? null);
  const comparando = modo === 'comparar';
  const listoComp = sel.length === 2 && a && b;

  function cambiarModo(v) {
    setModo(v);
    setSel([]);
    instRef.current?.limpiar();
  }

  return (
    <div>
      <div className="ign-ctrl">
        <div className="ign-modos" role="tablist">
          {[['explorar', 'Explorar'], ['comparar', 'Comparar dos']].map(([v, t]) => (
            <button key={v} role="tab" aria-selected={modo === v}
                    className={modo === v ? 'on' : ''}
                    onClick={() => cambiarModo(v)}>{t}</button>
          ))}
        </div>

        <label>
          <span>Año</span>
          <select value={anioSel} onChange={(e) => setAnioSel(e.target.value)}>
            {anios.map((y) => <option key={y} value={String(y)}>{y}</option>)}
          </select>
        </label>

        <label>
          <span>Vista</span>
          <select value={vista} onChange={(e) => setVista(e.target.value)}>
            <option value="continental">Continental</option>
            <option value="bicontinental">Bicontinental</option>
          </select>
        </label>

        <p className="ign-pista">
          {!comparando && 'Tocá una provincia para abrir su ficha.'}
          {comparando && sel.length === 0 && 'Elegí dos provincias, las que quieras.'}
          {comparando && sel.length === 1 && `${a?.nombre}. Falta una más.`}
          {comparando && sel.length === 2 && 'Listo, mirá la comparación.'}
        </p>
      </div>

      <div className="ign-lienzo">
        {/*
          El div de abajo lo maneja el componente vanilla, que le escribe el SVG
          adentro. React NO puede renderizar hijos ahí: cuando quisiera quitar
          alguno, ese nodo ya no es suyo y tira `removeChild` — un error que no
          rompe sólo el mapa, sino que vacía la isla entera y deja la tarjeta en
          blanco. Por eso el cartel de carga va afuera, como hermano.
        */}
        <div className="ign-marco" style={{ height: alto }}>
          <div className="ign-caja" ref={cajaRef} />
          {!listo && !error && <p className="ign-cargando">Cargando el mapa…</p>}
          {error && (
            <p className="ign-cargando">
              No se pudo cargar el mapa. Buscá tu provincia en la lista de más abajo.
            </p>
          )}
        </div>

        <div className="ign-panel">
          {activo ? (
            <>
              <p className="ign-nom">{activo.nombre}</p>
              <p className="ign-val">${fmt(activo.gasto_per_capita)}</p>
              <p className="ign-sub">de gasto por habitante en {anioSel}</p>
              <dl className="ign-lista">
                {FILAS.slice(0, 5).map(([txt, k, f]) => (
                  <div key={k}>
                    <dt>{txt}</dt>
                    <dd>{activo[k] == null ? '—' : f(activo[k])}</dd>
                  </div>
                ))}
              </dl>
              <p className="ign-ir">
                {comparando ? 'Tocá para elegirla' : 'Tocá para ver la ficha completa'}
              </p>
            </>
          ) : (
            <>
              <p className="ign-tit">Las 24 jurisdicciones</p>
              <p className="ign-ayuda">
                Pasá el mouse por cualquier provincia y sus números aparecen acá.
                Se puede arrastrar para mover el mapa y usar la rueda para acercar.
              </p>
              <p className="ign-territorio">{notaTerritorio}</p>
            </>
          )}
        </div>
      </div>

      {listoComp && (
        <div className="ign-comp">
          <h3 className="ign-c-tit">{a.nombre} <span>vs</span> {b.nombre}</h3>
          <div className="ign-scroll">
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
          </div>
          <p className="ign-c-links">
            <a href={`/provincia/${sel[0]}/`}>Ficha de {a.corto}</a>
            <a href={`/provincia/${sel[1]}/`}>Ficha de {b.corto}</a>
            <button onClick={() => { setSel([]); instRef.current?.limpiar(); }}>
              Empezar de nuevo
            </button>
          </p>
        </div>
      )}

      <p className="ign-atrib">{atribucion}</p>

      <style>{`
        .ign-ctrl { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 16px; margin-bottom: 16px; }
        .ign-ctrl label { display: flex; flex-direction: column; gap: 5px; }
        .ign-ctrl label span { font-size: .7rem; font-weight: 700; letter-spacing: .09em;
                               text-transform: uppercase; color: #64748B; }
        .ign-ctrl select { font-family: inherit; font-size: .92rem; font-weight: 600;
                           padding: 8px 13px; border-radius: 9px; border: 1px solid #C9D3E5;
                           background: #fff; color: #1A2B48; cursor: pointer; }
        .ign-ctrl select:hover { border-color: #D4AF37; }
        .ign-modos { display: flex; gap: 5px; }
        .ign-modos button { font-family: inherit; font-size: .86rem; font-weight: 600;
                            padding: 8px 15px; border-radius: 999px; cursor: pointer;
                            border: 1px solid #C9D3E5; background: #fff; color: #64748B; }
        .ign-modos button:hover { border-color: #D4AF37; color: #1A2B48; }
        .ign-modos button.on { background: #1A2B48; border-color: #1A2B48; color: #fff; }
        .ign-pista { margin-left: auto; font-size: .86rem; color: #64748B; }

        .ign-lienzo { display: grid; grid-template-columns: 1fr 268px; gap: 24px; align-items: start; }

        /* El componente ocupa el 100% del contenedor: si el div colapsa a 0 no
           se ve nada. Y overflow visible haría que el mapa se desborde al
           hacer zoom. Las dos cosas están advertidas en su documentación. */
        .ign-marco {
          position: relative; width: 100%; overflow: hidden;
          border-radius: 12px; background: #F7F9FC; border: 1px solid #DDE3EE;
        }
        .ign-caja {
          width: 100%; height: 100%; overflow: hidden;
          --mapar-fill: #43608F;
          --mapar-hover: #F0C338;
          --mapar-stroke: #ffffff;
          --mapar-stroke-w: 0.9;
          --mapar-sel-1: #1A2B48;
          --mapar-sel-2: #D4AF37;
        }
        .ign-cargando {
          position: absolute; inset: 0; display: grid; place-items: center;
          color: #94A3B8; font-size: .9rem; pointer-events: none;
        }

        .ign-panel { background: #F7F9FC; border: 1px solid #DDE3EE; border-radius: 12px;
                     padding: 20px; position: sticky; top: 84px; min-height: 240px; }
        .ign-tit, .ign-nom { font-size: .74rem; font-weight: 700; letter-spacing: .08em;
                             text-transform: uppercase; color: #64748B; }
        .ign-nom { color: #1A2B48; letter-spacing: .03em; font-size: .82rem; line-height: 1.35; }
        .ign-val { font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
                   font-size: 2.1rem; line-height: 1.05; color: #1A2B48; margin-top: 6px;
                   font-variant-numeric: tabular-nums; }
        .ign-sub { font-size: .78rem; color: #94A3B8; margin-top: 3px; }
        .ign-lista { margin-top: 14px; border-top: 1px solid #E3E9F3; padding-top: 11px; }
        .ign-lista > div { display: flex; justify-content: space-between; gap: 10px;
                           padding: 5px 0; font-size: .83rem; }
        .ign-lista dt { color: #64748B; }
        .ign-lista dd { font-weight: 600; color: #1E293B; white-space: nowrap;
                        font-variant-numeric: tabular-nums; }
        .ign-ir { margin-top: 12px; font-size: .76rem; color: #8A6D12; font-weight: 600; }
        .ign-ayuda { font-size: .9rem; color: #64748B; margin-top: 9px; line-height: 1.6; }
        .ign-territorio { font-size: .79rem; color: #94A3B8; margin-top: 14px;
                          padding-top: 12px; border-top: 1px solid #E3E9F3; line-height: 1.55; }

        .ign-comp { margin-top: 22px; border: 1px solid #DDE3EE; border-radius: 12px;
                    padding: 20px; background: #fff; }
        .ign-c-tit { font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
                     font-size: 1.4rem; color: #1A2B48; margin-bottom: 13px; line-height: 1.2; }
        .ign-c-tit span { color: #94A3B8; }
        .ign-scroll { overflow-x: auto; }
        .ign-comp table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
        .ign-comp th { font-size: .72rem; font-weight: 700; letter-spacing: .07em;
                       text-transform: uppercase; color: #64748B; text-align: right;
                       padding: 8px; border-bottom: 2px solid #DDE3EE; white-space: nowrap; }
        .ign-comp th:first-child { text-align: left; }
        .ign-comp td { padding: 10px 8px; border-bottom: 1px solid #EAEFF7;
                       text-align: right; font-size: .92rem; white-space: nowrap; }
        .ign-comp td:first-child { text-align: left; color: #64748B; }
        .ign-comp .mayor { font-weight: 700; color: #1A2B48; }
        .ign-comp .dif { color: #8A6D12; font-weight: 600; }
        .ign-comp tr.destacar { background: rgba(212,175,55,.1); }
        .ign-c-links { display: flex; flex-wrap: wrap; gap: 18px; align-items: center;
                       margin-top: 14px; font-size: .88rem; font-weight: 600; }
        .ign-c-links button { font-family: inherit; font-size: .85rem; font-weight: 600;
                              background: none; border: 0; cursor: pointer; color: #8A6D12;
                              text-decoration: underline; padding: 0; }
        .ign-atrib { font-size: .75rem; color: #94A3B8; margin-top: 14px;
                     font-weight: 600; letter-spacing: .02em; }

        @media (max-width: 860px) {
          .ign-lienzo { grid-template-columns: 1fr; }
          .ign-panel { position: static; min-height: 0; }
          .ign-pista { margin-left: 0; width: 100%; }
        }
      `}</style>
    </div>
  );
}

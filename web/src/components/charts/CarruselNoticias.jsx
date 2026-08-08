/**
 * CarruselNoticias.jsx — Las notas más recientes en la portada.
 *
 * Un carrusel es fácil de hacer mal: si se mueve solo, el lector pierde el
 * control de lo que está leyendo. Este no avanza automáticamente. Se pasa con
 * las flechas, con los puntos, con el teclado o arrastrando en el celular, y
 * las tarjetas que no están visibles siguen en el HTML para que Google las lea.
 */
import { useRef, useState } from 'react';

export default function CarruselNoticias({ notas, colores }) {
  const [i, setI] = useState(0);
  const pista = useRef(null);
  const total = notas.length;

  const ir = (n) => {
    const k = Math.max(0, Math.min(total - 1, n));
    setI(k);
    const el = pista.current?.children[k];
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
  };

  return (
    <div className="carr">
      <div className="carr-cab">
        <div>
          <p className="carr-eti">Noticias fiscales</p>
          <h2 className="carr-tit">Lo último</h2>
        </div>
        <div className="carr-nav">
          <button onClick={() => ir(i - 1)} disabled={i === 0} aria-label="Anterior">‹</button>
          <button onClick={() => ir(i + 1)} disabled={i === total - 1} aria-label="Siguiente">›</button>
          <a className="carr-todas" href="/noticias/">Ver todas</a>
        </div>
      </div>

      <div className="carr-pista" ref={pista}
           onScroll={(e) => {
             const w = e.target.firstChild?.offsetWidth || 1;
             setI(Math.round(e.target.scrollLeft / (w + 18)));
           }}>
        {notas.map((n) => (
          <a key={n.slug} className="carr-item" href={`/noticias/${n.slug}/`}>
            <div className="carr-top" style={{ background: colores[n.categoria] }}>
              <span className="carr-cat">{n.categoria}</span>
              <span className="carr-cifra">{n.cifra}</span>
              <span className="carr-pie">{n.cifraPie}</span>
            </div>
            <div className="carr-txt">
              <h3>{n.titulo}</h3>
              <p>{n.bajada}</p>
              <span className="carr-min">{n.minutos} min de lectura</span>
            </div>
          </a>
        ))}
      </div>

      <div className="carr-puntos">
        {notas.map((n, k) => (
          <button key={n.slug} onClick={() => ir(k)}
                  className={k === i ? 'on' : ''}
                  aria-label={`Ir a la nota ${k + 1} de ${total}`} />
        ))}
      </div>

      <style>{`
        .carr-cab { display: flex; align-items: flex-end; justify-content: space-between;
                    gap: 18px; margin-bottom: 16px; flex-wrap: wrap; }
        .carr-eti { font-size: .7rem; font-weight: 700; letter-spacing: .09em;
                    text-transform: uppercase; color: #64748B; }
        .carr-tit { font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
                    font-size: clamp(1.6rem, 3.2vw, 2.1rem); color: #1A2B48; margin-top: 3px; }
        .carr-nav { display: flex; align-items: center; gap: 8px; }
        .carr-nav button {
          width: 38px; height: 38px; border-radius: 50%; cursor: pointer;
          border: 1px solid #C9D3E5; background: #fff; color: #1A2B48;
          font-size: 1.4rem; line-height: 1; font-family: inherit;
        }
        .carr-nav button:hover:not(:disabled) { background: #1A2B48; color: #fff; border-color: #1A2B48; }
        .carr-nav button:disabled { opacity: .35; cursor: default; }
        .carr-todas { margin-left: 8px; font-size: .88rem; font-weight: 600; color: #2D4A7A; }

        .carr-pista {
          display: flex; gap: 18px; overflow-x: auto; scroll-snap-type: x mandatory;
          scrollbar-width: none; padding-bottom: 4px;
        }
        .carr-pista::-webkit-scrollbar { display: none; }
        .carr-item {
          flex: 0 0 clamp(260px, 31%, 340px); scroll-snap-align: start;
          display: flex; flex-direction: column; text-decoration: none; color: inherit;
          background: #fff; border: 1px solid #DDE3EE; border-radius: 18px;
          overflow: hidden; box-shadow: 0 1px 3px rgba(26,43,72,.07);
          transition: transform .18s ease, box-shadow .18s ease;
        }
        .carr-item:hover { transform: translateY(-3px); box-shadow: 0 12px 32px rgba(26,43,72,.14); }
        .carr-top { padding: 18px 20px 20px; color: #fff; }
        .carr-cat { display: block; font-size: .66rem; font-weight: 700;
                    letter-spacing: .1em; text-transform: uppercase; opacity: .82; }
        .carr-cifra { display: block; font-family: 'Barlow Condensed', sans-serif;
                      font-weight: 800; font-size: 2.2rem; line-height: 1.05; margin-top: 8px; }
        .carr-pie { display: block; font-size: .76rem; opacity: .85; margin-top: 2px; }
        .carr-txt { padding: 16px 20px 18px; display: flex; flex-direction: column; flex: 1; }
        .carr-txt h3 { font-size: 1rem; color: #1A2B48; line-height: 1.35; margin-bottom: 7px; }
        .carr-txt p { font-size: .86rem; color: #64748B; line-height: 1.55; }
        .carr-min { margin-top: auto; padding-top: 12px; font-size: .76rem; color: #94A3B8; }

        .carr-puntos { display: flex; justify-content: center; gap: 7px; margin-top: 16px; }
        .carr-puntos button {
          width: 8px; height: 8px; border-radius: 50%; border: 0; cursor: pointer;
          background: #C9D3E5; padding: 0; transition: width .2s ease, background .2s ease;
        }
        .carr-puntos button.on { width: 24px; border-radius: 4px; background: #1A2B48; }

        @media (max-width: 620px) {
          .carr-item { flex: 0 0 86%; }
          .carr-nav button { display: none; }
        }
      `}</style>
    </div>
  );
}

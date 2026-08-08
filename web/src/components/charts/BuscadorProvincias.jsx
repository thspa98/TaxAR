/**
 * BuscadorProvincias.jsx — Tabla buscable y ordenable de las 24 jurisdicciones.
 *
 * Es la puerta de entrada a las fichas: la mayoría de la gente llega al sitio
 * queriendo ver su propia provincia, no un ranking nacional. Por eso el
 * buscador va primero y acepta el nombre escrito sin tildes.
 */
import { useMemo, useState } from 'react';

const fmt = (v, dec = 0) =>
  v === null || v === undefined
    ? '—'
    : v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

const monto = (v) => {
  if (v === null || v === undefined) return '—';
  if (Math.abs(v) >= 1_000_000) return `${fmt(v / 1_000_000, 2)} bill.`;
  return `${fmt(v / 1000, 1)} mil M`;
};

// Buscar "cordoba" tiene que encontrar "Córdoba": nadie escribe las tildes.
const sinTildes = (s) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

const COLUMNAS = [
  { id: 'nombre', txt: 'Jurisdicción', tipo: 'texto' },
  { id: 'poblacion', txt: 'Habitantes', tipo: 'num' },
  { id: 'gasto', txt: 'Gasto total', tipo: 'num' },
  { id: 'per_capita', txt: 'Por habitante', tipo: 'num' },
  { id: 'dependencia', txt: 'Depende', tipo: 'num' },
  { id: 'resultado', txt: 'Resultado', tipo: 'num' },
];

export default function BuscadorProvincias({ items, anio }) {
  const [q, setQ] = useState('');
  const [orden, setOrden] = useState({ col: 'nombre', desc: false });

  const filas = useMemo(() => {
    const t = sinTildes(q.trim());
    const base = t
      ? items.filter((i) => sinTildes(i.nombre).includes(t) || sinTildes(i.region).includes(t))
      : items;
    const { col, desc } = orden;
    return [...base].sort((a, b) => {
      const va = a[col], vb = b[col];
      if (typeof va === 'string') return desc ? vb.localeCompare(va, 'es') : va.localeCompare(vb, 'es');
      return desc ? (vb ?? 0) - (va ?? 0) : (va ?? 0) - (vb ?? 0);
    });
  }, [items, q, orden]);

  const ordenar = (col) =>
    setOrden((o) => ({ col, desc: o.col === col ? !o.desc : col !== 'nombre' }));

  return (
    <div>
      <div className="buscador">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscá tu provincia o región…"
          aria-label="Buscar jurisdicción"
        />
        <span className="cuenta">
          {filas.length} de {items.length}
        </span>
      </div>

      <div className="scroll">
        <table>
          <thead>
            <tr>
              {COLUMNAS.map((c) => (
                <th key={c.id} className={c.tipo === 'num' ? 'der' : ''}>
                  <button onClick={() => ordenar(c.id)}
                          aria-label={`Ordenar por ${c.txt}`}
                          className={orden.col === c.id ? 'on' : ''}>
                    {c.txt}
                    <span className="flecha">{orden.col === c.id ? (orden.desc ? '▾' : '▴') : ''}</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filas.map((i) => (
              <tr key={i.slug} onClick={() => { window.location.href = `/provincia/${i.slug}/`; }}>
                <td>
                  <a href={`/provincia/${i.slug}/`}>{i.nombre}</a>
                  <span className="reg">
                    {i.region}
                    {i.atrasada && (
                      <b className="viejo" title={`No reportó ${anio}; última cifra de ${i.anio}`}>
                        dato de {i.anio}
                      </b>
                    )}
                  </span>
                </td>
                <td className="der">{fmt(i.poblacion)}</td>
                <td className="der">{monto(i.gasto)}</td>
                <td className="der">
                  <strong>${fmt(i.per_capita)}</strong>
                  <span className="pto-rank">{i.puesto_pc}°</span>
                </td>
                <td className="der">{fmt(i.dependencia, 1)}%</td>
                <td className={`der ${i.resultado >= 0 ? 'sup' : 'def'}`}>
                  {i.resultado >= 0 ? '+' : ''}{fmt(i.resultado, 1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filas.length === 0 && (
        <p className="vacio">No encontramos ninguna jurisdicción con ese nombre.</p>
      )}

      <style>{`
        .buscador { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
        .buscador input {
          flex: 1; font-family: inherit; font-size: 1rem;
          padding: 11px 16px; border-radius: 10px;
          border: 1px solid #C9D3E5; background: #fff; color: #1E293B;
        }
        .buscador input:focus { outline: 3px solid #D4AF37; outline-offset: 1px; border-color: #D4AF37; }
        .cuenta { font-size: .8rem; color: #94A3B8; white-space: nowrap; }

        .scroll { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
        th { padding: 0 0 8px; border-bottom: 2px solid #DDE3EE; }
        th.der { text-align: right; }
        th button {
          background: none; border: 0; cursor: pointer; font-family: inherit;
          font-size: .72rem; font-weight: 700; letter-spacing: .07em;
          text-transform: uppercase; color: #64748B; padding: 4px 6px;
          border-radius: 6px; white-space: nowrap;
        }
        th.der button { margin-left: auto; display: block; }
        th button:hover { color: #1A2B48; background: rgba(26,43,72,.06); }
        th button.on { color: #1A2B48; }
        .flecha { margin-left: 3px; }

        td { padding: 11px 8px; border-bottom: 1px solid #EAEFF7; font-size: .93rem; }
        td.der { text-align: right; }
        tbody tr { cursor: pointer; }
        tbody tr:hover { background: rgba(212,175,55,.09); }
        td a { font-weight: 600; color: #1A2B48; text-decoration: none; }
        tbody tr:hover td a { text-decoration: underline; text-decoration-color: #D4AF37; }
        .reg { display: block; font-size: .74rem; color: #94A3B8; }
        .viejo { display: inline-block; margin-left: 7px; font-weight: 600;
                 color: #B45309; background: rgba(180,83,9,.1);
                 border: 1px solid rgba(180,83,9,.26);
                 padding: 1px 7px; border-radius: 999px; font-size: .68rem; }
        .pto-rank { display: inline-block; margin-left: 7px; font-size: .74rem;
                    color: #94A3B8; min-width: 22px; }
        .sup { color: #059669; font-weight: 600; }
        .def { color: #DC2626; font-weight: 600; }
        .vacio { text-align: center; color: #64748B; padding: 30px 0; }

        /* En celular, seis columnas obligan a un scroll horizontal incómodo.
           Se ocultan las dos menos decisivas —habitantes y gasto total— y
           quedan las que sirven para comparar: por habitante, dependencia y
           resultado. Los datos completos están en la ficha de cada una. */
        @media (max-width: 720px) {
          .buscador { flex-direction: column; align-items: stretch; gap: 8px; }
          .cuenta { text-align: right; }
          th:nth-child(2), td:nth-child(2),
          th:nth-child(3), td:nth-child(3) { display: none; }
          td { padding: 10px 6px; font-size: .88rem; }
          .pto-rank { display: block; margin-left: 0; }
        }
      `}</style>
    </div>
  );
}

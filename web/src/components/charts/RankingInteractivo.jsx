/**
 * RankingInteractivo.jsx — Ranking de provincias con año, métrica y filtro.
 *
 * Es la pieza que se repite en casi todo el sitio, así que recibe los datos
 * ya calculados desde Astro y no hace ninguna cuenta propia: si el número
 * cambia, cambia en el ETL, en un solo lugar.
 */
import { useMemo, useState } from 'react';
import {
  Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

const COLOR_REGION = {
  GBA: '#1A2B48',
  Pampeana: '#2D4A7A',
  NOA: '#D4AF37',
  NEA: '#C08A2E',
  Cuyo: '#0F766E',
  Patagonia: '#3B82F6',
};

const fmt = (v, dec = 0) =>
  v === null || v === undefined
    ? 'sin dato'
    : v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

function formatear(valor, unidad) {
  if (valor === null || valor === undefined) return 'sin dato';
  if (unidad === 'pesos') return `$${fmt(valor)}`;
  if (unidad === 'pct') return `${fmt(valor, 1)}%`;
  if (unidad === 'millones') {
    if (Math.abs(valor) >= 1_000_000) return `${fmt(valor / 1_000_000, 2)} billones`;
    return `${fmt(valor / 1000, 1)} mil M`;
  }
  return fmt(valor);
}

function Tip({ active, payload, unidad, sufijo }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{
      background: '#fff', border: '1px solid #DDE3EE', borderRadius: 10,
      padding: '10px 13px', boxShadow: '0 8px 26px rgba(26,43,72,.14)', fontSize: 13,
    }}>
      <div style={{ fontWeight: 700, color: '#1A2B48', marginBottom: 3 }}>{d.nombreLargo}</div>
      <div style={{ color: '#1E293B' }}>
        {formatear(d.valor, unidad)} {sufijo}
      </div>
      <div style={{ color: '#64748B', fontSize: 12, marginTop: 4 }}>
        Puesto {d.puesto} de {d.total} · región {d.region}
      </div>
    </div>
  );
}

export default function RankingInteractivo({
  datosPorAnio,          // { "2024": [{slug, nombre, nombreLargo, region, valor, puesto}], ... }
  anios,
  anioInicial,
  unidad = 'pesos',
  sufijo = '',
  destacar = [],
  altura = 560,
}) {
  const [anio, setAnio] = useState(String(anioInicial));
  const [region, setRegion] = useState('todas');

  const regiones = useMemo(() => {
    const s = new Set();
    Object.values(datosPorAnio).forEach((arr) => arr.forEach((d) => s.add(d.region)));
    return ['todas', ...[...s].sort()];
  }, [datosPorAnio]);

  const datos = useMemo(() => {
    const base = datosPorAnio[anio] ?? [];
    const total = base.length;
    return base
      .filter((d) => region === 'todas' || d.region === region)
      .map((d) => ({ ...d, total }));
  }, [datosPorAnio, anio, region]);

  if (!datos.length) {
    return <p style={{ color: '#64748B' }}>No hay datos para {anio}.</p>;
  }

  const max = datos[0].valor;
  const min = datos[datos.length - 1];
  const brecha = min.valor ? (max / min.valor).toFixed(1).replace('.', ',') : null;

  return (
    <div>
      <div className="controles">
        <label>
          <span className="ctrl-lbl">Año</span>
          <select value={anio} onChange={(e) => setAnio(e.target.value)}>
            {anios.map((a) => <option key={a} value={String(a)}>{a}</option>)}
          </select>
        </label>

        <label>
          <span className="ctrl-lbl">Región</span>
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {regiones.map((r) => (
              <option key={r} value={r}>{r === 'todas' ? 'Todo el país' : r}</option>
            ))}
          </select>
        </label>

        {brecha && region === 'todas' && (
          <p className="brecha">
            La primera gasta <strong>{brecha} veces</strong> lo de la última
          </p>
        )}
      </div>

      <div style={{ width: '100%', height: altura }}>
        <ResponsiveContainer>
          <BarChart data={datos} layout="vertical" margin={{ top: 4, right: 74, left: 4, bottom: 4 }}>
            <XAxis type="number" hide domain={[0, 'dataMax']} />
            <YAxis
              type="category"
              dataKey="nombre"
              width={126}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12.5, fill: '#1E293B' }}
            />
            <Tooltip
              content={<Tip unidad={unidad} sufijo={sufijo} />}
              cursor={{ fill: 'rgba(26,43,72,.05)' }}
            />
            <Bar dataKey="valor" radius={[0, 5, 5, 0]} isAnimationActive={false}
                 label={{
                   position: 'right',
                   fontSize: 11.5,
                   fill: '#64748B',
                   formatter: (v) => formatear(v, unidad),
                 }}>
              {datos.map((d) => (
                <Cell
                  key={d.slug}
                  fill={COLOR_REGION[d.region] ?? '#2D4A7A'}
                  fillOpacity={destacar.length && !destacar.includes(d.slug) ? 0.45 : 1}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <ul className="leyenda">
        {Object.entries(COLOR_REGION).map(([r, c]) => (
          <li key={r}><i style={{ background: c }} />{r}</li>
        ))}
      </ul>

      <style>{`
        .controles {
          display: flex; flex-wrap: wrap; align-items: flex-end; gap: 16px; margin-bottom: 18px;
        }
        .controles label { display: flex; flex-direction: column; gap: 5px; }
        .ctrl-lbl {
          font-size: .7rem; font-weight: 700; letter-spacing: .09em;
          text-transform: uppercase; color: #64748B;
        }
        .controles select {
          font-family: inherit; font-size: .92rem; font-weight: 600;
          padding: 8px 13px; border-radius: 9px;
          border: 1px solid #C9D3E5; background: #fff; color: #1A2B48;
          cursor: pointer; min-width: 148px;
        }
        .controles select:hover { border-color: #D4AF37; }
        .brecha {
          margin-left: auto; font-size: .89rem; color: #64748B;
          background: rgba(212,175,55,.14); border: 1px solid rgba(212,175,55,.38);
          padding: 7px 14px; border-radius: 999px;
        }
        .brecha strong { color: #8A6D12; }
        .leyenda {
          display: flex; flex-wrap: wrap; gap: 15px; list-style: none;
          margin-top: 14px; font-size: .79rem; color: #64748B;
        }
        .leyenda li { display: flex; align-items: center; gap: 6px; }
        .leyenda i { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
        @media (max-width: 620px) {
          .brecha { margin-left: 0; }
          .controles select { min-width: 0; width: 100%; }
          .controles label { flex: 1 1 130px; }
        }
      `}</style>
    </div>
  );
}

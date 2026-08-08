/**
 * SerieNominalConstante.jsx — El gráfico que evita la conclusión equivocada.
 *
 * Con la inflación argentina, una serie de gasto en pesos corrientes siempre
 * sube y siempre parece un descontrol. La misma serie ajustada por inflación
 * suele contar lo contrario. Mostrar las dos juntas, y dejar que el lector
 * cambie de una a otra, es más honesto que elegir por él.
 */
import { useMemo, useState } from 'react';
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

const fmt = (v, dec = 0) =>
  v === null || v === undefined
    ? 'sin dato'
    : v.toLocaleString('es-AR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

const corto = (v) => {
  if (v === null || v === undefined) return '';
  if (Math.abs(v) >= 1_000_000) return `${fmt(v / 1_000_000, 1)} bill.`;
  if (Math.abs(v) >= 1000) return `${fmt(v / 1000, 0)} mil M`;
  return fmt(v);
};

function Tip({ active, payload, label, modo, anioBase }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{
      background: '#fff', border: '1px solid #DDE3EE', borderRadius: 10,
      padding: '11px 14px', boxShadow: '0 8px 26px rgba(26,43,72,.14)', fontSize: 13,
    }}>
      <div style={{ fontWeight: 700, color: '#1A2B48', marginBottom: 5 }}>{label}</div>
      {modo !== 'constante' && (
        <div>Corrientes: <strong>{fmt(d.nominal)}</strong> M</div>
      )}
      {modo !== 'nominal' && (
        <div style={{ color: d.constante === null ? '#94A3B8' : '#1E293B' }}>
          Constantes: <strong>{d.constante === null ? 'sin IPC' : `${fmt(d.constante)} M`}</strong>
        </div>
      )}
      {modo === 'constante' && d.constante !== null && (
        <div style={{ color: '#64748B', fontSize: 11.5, marginTop: 4 }}>
          en pesos de {anioBase}
        </div>
      )}
    </div>
  );
}

export default function SerieNominalConstante({
  serie,               // [{ anio, gastos_totales, gastos_constantes }]
  anioBase,
  altura = 380,
}) {
  const [modo, setModo] = useState('constante');

  /**
   * El eje arranca donde el modo elegido tiene algo que mostrar.
   *
   * La serie deflactada empieza en 2017, cuando arranca el IPC oficial. Si el
   * gráfico igual dibujaba desde 2005, los doce años previos quedaban vacíos
   * del lado constante y aplastaban la línea nominal contra el piso: doce años
   * de gráfico sin información que además arruinaban la escala.
   *
   * En "pesos corrientes" sí se muestra todo, porque ahí la serie larga existe
   * y tiene sentido.
   */
  const datos = useMemo(() => {
    const todo = serie.map((f) => ({
      anio: f.anio,
      nominal: f.gastos_totales,
      constante: f.gastos_constantes,
    }));
    if (modo === 'nominal') return todo;
    const desde = todo.findIndex((d) => d.constante !== null);
    return desde > 0 ? todo.slice(desde) : todo;
  }, [serie, modo]);

  const completa = serie.length;
  const recortada = modo !== 'nominal' && datos.length < completa;

  const conIpc = datos.filter((d) => d.constante !== null);
  const variacion = conIpc.length > 1
    ? ((conIpc.at(-1).constante / conIpc[0].constante - 1) * 100)
    : null;
  // El "se multiplicó por X" se calcula sobre la serie completa, no sobre el
  // recorte: es el dato que da la magnitud real de la inflación.
  const varNominal = serie.length > 1 && serie[0].gastos_totales
    ? (serie.at(-1).gastos_totales / serie[0].gastos_totales)
    : null;

  return (
    <div>
      <div className="tabs" role="tablist">
        {[
          ['constante', 'Ajustado por inflación'],
          ['nominal', 'Pesos corrientes'],
          ['ambos', 'Los dos'],
        ].map(([v, t]) => (
          <button key={v} role="tab" aria-selected={modo === v}
                  className={modo === v ? 'on' : ''}
                  onClick={() => setModo(v)}>
            {t}
          </button>
        ))}
      </div>

      <div style={{ width: '100%', height: altura }}>
        <ResponsiveContainer>
          <LineChart data={datos} margin={{ top: 10, right: 18, left: 6, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E6EBF4" vertical={false} />
            <XAxis dataKey="anio" tickLine={false} axisLine={{ stroke: '#DDE3EE' }}
                   tick={{ fontSize: 11.5, fill: '#64748B' }} />
            <YAxis tickFormatter={corto} tickLine={false} axisLine={false} width={72}
                   tick={{ fontSize: 11.5, fill: '#64748B' }} />
            <Tooltip content={<Tip modo={modo} anioBase={anioBase} />} />
            {modo !== 'constante' && (
              <Line type="monotone" dataKey="nominal" name="Pesos corrientes"
                    stroke="#D4AF37" strokeWidth={2.4} dot={false} isAnimationActive={false} />
            )}
            {modo !== 'nominal' && (
              <Line type="monotone" dataKey="constante" name="Pesos constantes"
                    stroke="#1A2B48" strokeWidth={2.8} dot={false}
                    connectNulls={false} isAnimationActive={false} />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {variacion !== null && (
        <p className="lectura">
          En pesos corrientes el gasto se multiplicó por{' '}
          <strong>{fmt(varNominal, 0)}</strong> desde {serie[0].anio}. Descontada la
          inflación, entre {conIpc[0].anio} y {conIpc.at(-1).anio}{' '}
          <strong className={variacion < 0 ? 'baja' : 'sube'}>
            {variacion < 0 ? 'cayó' : 'creció'} {fmt(Math.abs(variacion), 1)}%
          </strong>.
        </p>
      )}

      {recortada && (
        <p className="recorte">
          El gráfico arranca en {datos[0].anio} porque el IPC oficial del INDEC empieza en
          diciembre de 2016. Para ver la serie desde {serie[0].anio}, elegí
          {' '}<button onClick={() => setModo('nominal')}>pesos corrientes</button>.
        </p>
      )}

      <style>{`
        .tabs { display: flex; gap: 6px; margin-bottom: 16px; flex-wrap: wrap; }
        .tabs button {
          font-family: inherit; font-size: .85rem; font-weight: 600;
          padding: 7px 14px; border-radius: 999px;
          border: 1px solid #C9D3E5; background: #fff; color: #64748B; cursor: pointer;
          transition: all .15s ease;
        }
        .tabs button:hover { border-color: #D4AF37; color: #1A2B48; }
        .tabs button.on { background: #1A2B48; border-color: #1A2B48; color: #fff; }
        .lectura {
          margin-top: 14px; font-size: .92rem; color: #64748B;
          padding: 13px 16px; background: #F2F5FA; border-radius: 10px;
          border: 1px solid #DDE3EE;
        }
        .lectura strong { color: #1A2B48; }
        .lectura .baja { color: #DC2626; }
        .lectura .sube { color: #059669; }
        .recorte { margin-top: 9px; font-size: .82rem; color: #94A3B8; line-height: 1.55; }
        .recorte button {
          font-family: inherit; font-size: inherit; font-weight: 600; cursor: pointer;
          background: none; border: 0; padding: 0; color: #2D4A7A; text-decoration: underline;
        }
        @media (max-width: 620px) {
          .tabs { gap: 4px; }
          .tabs button { flex: 1; padding: 8px 6px; font-size: .8rem; text-align: center; }
          .lectura { font-size: .87rem; padding: 11px 13px; }
        }
      `}</style>
    </div>
  );
}

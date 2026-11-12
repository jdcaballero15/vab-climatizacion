import { useState } from "react";

import type { Dashboard } from "./useDashboard";

type Week = Dashboard["weeks"][number];

// Dos series con orden fijo de la paleta categórica (validada: CVD y contraste vs. blanco).
const SERIES = { created: "#2a78d6", done: "#eb6834" } as const;
const LABELS = { created: "Creadas", done: "Terminadas" } as const;

function weekLabel(day: string): string {
  const [, month, date] = day.split("-");
  return `${date}/${month}`;
}

/**
 * Evolución por semana: barras agrupadas de creadas y terminadas (E10-01). Leyenda arriba,
 * valor de cada barra al pasar o enfocar, y la misma información como tabla.
 */
export function WeeklyChart({ weeks }: { weeks: Week[] }) {
  const [active, setActive] = useState<{ week: Week; key: keyof typeof LABELS } | null>(null);
  const [asTable, setAsTable] = useState(false);
  const max = Math.max(1, ...weeks.flatMap((w) => [w.created, w.done]));
  const height = 160;
  const slot = 48;
  const bar = 16;
  const width = Math.max(weeks.length * slot, 240);

  return (
    <div className="dashboard__chart">
      <div className="dashboard__legend">
        {(Object.keys(LABELS) as (keyof typeof LABELS)[]).map((key) => (
          <span key={key}>
            <i style={{ background: SERIES[key] }} aria-hidden="true" /> {LABELS[key]}
          </span>
        ))}
        <button type="button" className="btn--ghost btn--sm" onClick={() => setAsTable((t) => !t)}>
          {asTable ? "Ver gráfico" : "Ver tabla"}
        </button>
      </div>
      {asTable ? (
        <table className="parts__table" aria-label="Órdenes por semana">
          <thead>
            <tr>
              <th scope="col">Semana del</th>
              <th scope="col">Creadas</th>
              <th scope="col">Terminadas</th>
            </tr>
          </thead>
          <tbody>
            {weeks.map((week) => (
              <tr key={week.week_start}>
                <td>{weekLabel(week.week_start)}</td>
                <td>{week.created}</td>
                <td>{week.done}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <svg
          viewBox={`0 0 ${width} ${height + 24}`}
          className="dashboard__svg"
          role="img"
          aria-label="Órdenes creadas y terminadas por semana"
        >
          <line x1={0} x2={width} y1={height} y2={height} className="dashboard__baseline" />
          {weeks.map((week, index) =>
            (["created", "done"] as const).map((key, offset) => {
              const value = week[key];
              const h = (value / max) * (height - 8);
              const x = index * slot + 6 + offset * (bar + 2);
              return (
                <g key={`${week.week_start}-${key}`}>
                  <rect
                    x={x}
                    y={height - h}
                    width={bar}
                    height={Math.max(h, value ? 2 : 0)}
                    rx={4}
                    fill={SERIES[key]}
                    tabIndex={0}
                    aria-label={`${LABELS[key]} la semana del ${weekLabel(week.week_start)}: ${value}`}
                    onPointerEnter={() => setActive({ week, key })}
                    onFocus={() => setActive({ week, key })}
                    onPointerLeave={() => setActive(null)}
                    onBlur={() => setActive(null)}
                  />
                </g>
              );
            }),
          )}
          {weeks.map((week, index) => (
            <text
              key={week.week_start}
              x={index * slot + 6 + bar}
              y={height + 16}
              textAnchor="middle"
              className="dashboard__tick"
            >
              {weekLabel(week.week_start)}
            </text>
          ))}
        </svg>
      )}
      <p className="dashboard__readout" aria-live="polite">
        {active
          ? `Semana del ${weekLabel(active.week.week_start)}: ${active.week.created} creadas, ${active.week.done} terminadas`
          : " "}
      </p>
    </div>
  );
}

/** Ranking horizontal de una sola serie: el valor como texto al lado de cada barra. */
export function Ranking({
  items,
  empty,
  unit,
}: {
  items: { key: string; label: string; value: number; display: string }[];
  empty: string;
  unit?: string;
}) {
  if (items.length === 0) {
    return <p className="muted">{empty}</p>;
  }
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <ol className="dashboard__ranking">
      {items.map((item) => (
        <li key={item.key} title={`${item.label}: ${item.display}${unit ?? ""}`}>
          <span className="dashboard__ranking-label">{item.label}</span>
          <span className="dashboard__ranking-track">
            <span
              className="dashboard__ranking-bar"
              style={{ width: `${(item.value / max) * 100}%`, background: SERIES.created }}
            />
          </span>
          <span className="dashboard__ranking-value">{item.display}</span>
        </li>
      ))}
    </ol>
  );
}

"use client";

import type { Inference } from "../lib/types";

function buildPath(
  values: number[],
  width = 760,
  height = 220,
) {
  if (!values.length) return "";

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return values
    .map((value, index) => {
      const x =
        (index / Math.max(values.length - 1, 1)) *
        width;

      const y =
        height -
        ((value - min) / range) *
          (height - 24) -
        12;

      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export default function SignalChart({
  data,
}: {
  data: Inference[];
}) {
  const values = data
    .slice(-80)
    .map((item) => item.signal_value);

  const path = buildPath(values);

  const min = values.length
    ? Math.min(...values)
    : 0;

  const max = values.length
    ? Math.max(...values)
    : 0;

  return (
    <div className="chart-wrap">
      <div className="chart-meta">
        <span>Últimas {values.length} amostras</span>
        <span>
          min {min.toFixed(3)} · max {max.toFixed(3)}
        </span>
      </div>

      <svg
        viewBox="0 0 760 220"
        preserveAspectRatio="none"
        className="signal-svg"
        role="img"
        aria-label="Sinal de vibração"
      >
        <line
          x1="0"
          y1="55"
          x2="760"
          y2="55"
          className="grid-line"
        />

        <line
          x1="0"
          y1="110"
          x2="760"
          y2="110"
          className="grid-line"
        />

        <line
          x1="0"
          y1="165"
          x2="760"
          y2="165"
          className="grid-line"
        />

        {path ? (
          <path
            d={path}
            className="signal-path"
            fill="none"
            strokeWidth="2"
          />
        ) : null}
      </svg>
    </div>
  );
}
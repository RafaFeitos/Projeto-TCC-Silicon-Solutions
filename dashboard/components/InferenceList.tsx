"use client";

import type { Inference } from "../lib/types";

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatTime(value: string) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleTimeString("pt-BR");
}

export default function InferenceList({
  data,
}: {
  data: Inference[];
}) {
  return (
    <div className="inference-list">
      {data.length === 0 ? (
        <div className="empty">
          Inicie o replay para gerar inferências.
        </div>
      ) : (
        data.map((item, index) => (
          <div
            className="inference-row"
            key={`${item.timestamp}-${index}`}
          >
            <div>
              <strong>
                {item.predicted_class.replaceAll("_", " ")}
              </strong>

              <span>{formatTime(item.timestamp)}</span>
            </div>

            <div className="confidence">
              <span>{pct(item.confidence)}</span>

              <div className="confidence-track">
                <i
                  style={{
                    width: `${
                      Math.max(
                        0,
                        Math.min(1, item.confidence),
                      ) * 100
                    }%`,
                  }}
                />
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.config import DATA_DIR, WINDOW_SIZE, RMS_CRITICAL, RMS_WARNING


@dataclass
class Sample:
    timestamp: datetime
    signal: float
    label: str | None = None
    source_row: int = 0


TIME_ALIASES = ["timestamp", "time", "datetime", "date", "t"]
SIGNAL_ALIASES = ["vibration", "vib", "acceleration", "accel", "amplitude", "signal", "value"]
LABEL_ALIASES = ["label", "class", "classe", "state", "status"]
CONF_ALIASES = ["confidence", "score", "probability", "prob"]
X_ALIASES = ["ax", "acc_x", "accel_x", "x"]
Y_ALIASES = ["ay", "acc_y", "accel_y", "y"]
Z_ALIASES = ["az", "acc_z", "accel_z", "z"]


def _find_column(columns: list[str], aliases: list[str]) -> str | None:
    normalized = {c.strip().lower(): c for c in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    for c in columns:
        lc = c.strip().lower()
        if any(alias in lc for alias in aliases):
            return c
    return None


def find_csv() -> Path:
    files = sorted(p for p in DATA_DIR.glob("*.csv") if not p.name.startswith("maquina_demo"))
    if not files:
        demo = DATA_DIR / "maquina_demo.csv"
        files = [demo] if demo.exists() else []
    if not files:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em {DATA_DIR}. Coloque o dataset da maquina nessa pasta."
        )
    return files[0]


def _parse_time(value: str | None, index: int) -> datetime:
    if value:
        text = value.strip()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(index, tz=timezone.utc)


def load_samples(path: Path | None = None) -> tuple[list[Sample], dict]:
    path = path or find_csv()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV sem cabeçalho.")
        columns = [c.strip() for c in reader.fieldnames if c]
        time_col = _find_column(columns, TIME_ALIASES)
        label_col = _find_column(columns, LABEL_ALIASES)
        signal_col = _find_column(columns, SIGNAL_ALIASES)
        x_col = _find_column(columns, X_ALIASES)
        y_col = _find_column(columns, Y_ALIASES)
        z_col = _find_column(columns, Z_ALIASES)

        if not signal_col and not all([x_col, y_col, z_col]):
            raise ValueError(
                "Não foi possível encontrar a coluna de vibração nem as colunas ax/ay/az. "
                f"Colunas encontradas: {columns}"
            )

        samples: list[Sample] = []
        for idx, row in enumerate(reader):
            try:
                if signal_col:
                    value = float(row[signal_col])
                else:
                    x = float(row[x_col])
                    y = float(row[y_col])
                    z = float(row[z_col])
                    value = math.sqrt(x * x + y * y + z * z)
            except (TypeError, ValueError):
                continue
            label = row.get(label_col) if label_col else None
            samples.append(
                Sample(
                    timestamp=_parse_time(row.get(time_col) if time_col else None, idx),
                    signal=value,
                    label=label.strip() if isinstance(label, str) and label.strip() else None,
                    source_row=idx,
                )
            )

    meta = {
        "file_name": path.name,
        "rows": len(samples),
        "signal_column": signal_col or "sqrt(ax² + ay² + az²)",
        "label_column": label_col,
        "timestamp_column": time_col,
        "columns": columns,
    }
    return samples, meta


def rms(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return math.sqrt(sum(v * v for v in vals) / len(vals))


def confidence_from_rms(value: float) -> float:
    if value >= RMS_CRITICAL:
        return min(0.99, 0.85 + min(0.14, (value - RMS_CRITICAL)))
    if value >= RMS_WARNING:
        span = max(0.01, RMS_CRITICAL - RMS_WARNING)
        return min(0.89, 0.65 + 0.24 * ((value - RMS_WARNING) / span))
    return max(0.50, min(0.99, 0.96 - value * 0.15))


def infer_window(window: list[Sample]) -> dict:
    value = window[-1].signal
    window_rms = rms(s.signal for s in window[-WINDOW_SIZE:])

    if window_rms >= RMS_CRITICAL:
        predicted = "VIBRACAO_ANORMAL"
        state = "ANOMALIA"
        severity = "CRITICAL"
        alert = "Vibração anormal persistente"
    elif window_rms >= RMS_WARNING:
        predicted = "VIBRACAO_ANORMAL"
        state = "ANOMALIA"
        severity = "WARNING"
        alert = "Vibração acima do padrão"
    else:
        predicted = "NORMAL"
        state = "OPERANDO"
        severity = None
        alert = None

    return {
        "timestamp": window[-1].timestamp,
        "predicted_class": predicted,
        "confidence": confidence_from_rms(window_rms),
        "model_version": "demo_rms_v1",
        "source": "demo_rms",
        "signal_value": value,
        "rms": window_rms,
        "state": state,
        "alert": alert,
        "severity": severity,
        "reference_label": window[-1].label,
    }
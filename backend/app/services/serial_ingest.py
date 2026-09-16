from __future__ import annotations

import asyncio
import csv
import math
import unicodedata
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Awaitable, Callable

import serial

from app.config import (
    CSV_SAVE_INTERVAL_SECONDS,
    SERIAL_RECONNECT_SECONDS,
    SERIAL_WINDOW_SAMPLES,
)


EmitCallback = Callable[[dict], Awaitable[None]]


class SerialIngestor:
    def __init__(
        self,
        machine_id: int,
        port: str,
        baud: int,
        csv_path: Path,
    ) -> None:
        self.machine_id = machine_id
        self.port = port
        self.baud = baud
        self.csv_path = csv_path
        self._running = False
        self._cursor = 0
        self._signals: deque[float] = deque(
            maxlen=SERIAL_WINDOW_SAMPLES
        )

        self._sample_buffer: list[dict] = []
        self._last_flush = monotonic()
        self._metadata: dict[str, str] = {}
        self._predicted_class = "AGUARDANDO"
        self._confidence = 0.0
        self._rpm_raw: float | None = None
        self._rpm_filtered: float | None = None
        self._rpm_pulses: int | None = None
        self._rpm_pulse_hz: float | None = None
        self._temperature_c: float | None = None
        self._ntc_raw: int | None = None
        self._ntc_voltage: float | None = None
        self._ntc_resistance: float | None = None

    @property
    def running(self) -> bool:
        return self._running

    def stop(self) -> None:
        self._running = False

    def status(self) -> dict:
        return {
            "running": self._running,
            "cursor": self._cursor,
            "total": 0,
        }

    async def run(
        self,
        emit: EmitCallback,
    ) -> None:
        if self._running:
            return

        self._running = True

        try:
            while self._running:
                try:
                    connection = serial.Serial(
                        port=self.port,
                        baudrate=self.baud,
                        timeout=1,
                    )

                    try:
                        while self._running:
                            raw = await asyncio.to_thread(
                                connection.readline
                            )
                            if raw:
                                line = raw.decode(
                                    "utf-8",
                                    errors="ignore",
                                ).strip()
                                item = self._parse_line(line)
                                if item is not None:
                                    self._cursor += 1
                                    await emit(item)
                            self._flush_if_needed()
                    finally:
                        if connection.is_open:
                            connection.close()
                            
                except serial.SerialException:
                    if not self._running:
                        break

                    await asyncio.sleep(
                        SERIAL_RECONNECT_SECONDS
                    )

        finally:
            self._running = False
            self._flush_csv()

    def _parse_line(
        self,
        line: str,
    ) -> dict | None:
        if not line.startswith("@"):
            return None
        parts = [
            part.strip()
            for part in line.split(",")
        ]

        prefix = parts[0].upper()

        if prefix == "@M":
            self._parse_metadata(parts)
            return None
        if prefix == "@S":
            self._parse_sample(parts)
            return None
        if prefix == "@R":
            self._parse_rpm(parts)
            return None
        if prefix == "@T":
            self._parse_temperature(parts)
            return None
        if prefix == "@I":
            return self._parse_inference(parts)

        return None

    def _parse_metadata(
        self,
        parts: list[str],
    ) -> None:
        if len(parts) >= 3:
            key = parts[1].strip().lower()

            value = ",".join(
                parts[2:]
            ).strip()

            if key:
                self._metadata[key] = value

    def _parse_sample(
        self,
        parts: list[str],
    ) -> None:
        if len(parts) >= 5:
            device_timestamp = parts[1]
            x, y, z = map(
                float,
                parts[2:5],
            )
        elif len(parts) >= 4:
            device_timestamp = ""
            x, y, z = map(
                float,
                parts[1:4],
            )
        else:
            return
        signal = math.sqrt(
            x * x +
            y * y +
            z * z
        )

        self._signals.append(signal)

        self._sample_buffer.append({
            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),
            "device_timestamp":
                device_timestamp,
            "accel_x": x,
            "accel_y": y,
            "accel_z": z,
            "signal": signal,
            "rpm_raw":
                self._rpm_raw,
            "rpm_filtered":
                self._rpm_filtered,
            "temperature_c":
                self._temperature_c,
            "predicted_class":
                self._predicted_class,
            "confidence":
                self._confidence,
        })
    def _parse_rpm(
        self,
        parts: list[str],
    ) -> None:
        if len(parts) < 6:
            return
        self._rpm_raw = self._float_or_none(
            parts[2]
        )
        self._rpm_filtered = self._float_or_none(
            parts[3]
        )
        self._rpm_pulses = self._int_or_none(
            parts[4]
        )
        self._rpm_pulse_hz = self._float_or_none(
            parts[5]
        )

    def _parse_temperature(
        self,
        parts: list[str],
    ) -> None:
        if len(parts) < 6:
            return
        self._temperature_c = self._float_or_none(
            parts[2]
        )
        self._ntc_raw = self._int_or_none(
            parts[3]
        )
        self._ntc_voltage = self._float_or_none(
            parts[4]
        )
        self._ntc_resistance = self._float_or_none(
            parts[5]
        )

    def _parse_inference(
        self,
        parts: list[str],
    ) -> dict | None:
        if len(parts) < 4:
            return None
        self._predicted_class = (
            parts[2]
            or "AGUARDANDO"
        )
        confidence = self._float_or_none(
            parts[3]
        )
        if confidence is None:
            confidence = 0.0
        if confidence > 1:
            confidence /= 100.0
        self._confidence = max(
            0.0,
            min(1.0, confidence),
        )
        state, alert, severity = (
            self._state_from_class(
                self._predicted_class
            )
        )
        return {
            "machine_id":
                self.machine_id,
            "timestamp":
                datetime.now(timezone.utc),
            "predicted_class":
                self._predicted_class,
            "confidence":
                self._confidence,
            "model_version":
                self._metadata.get(
                    "model_version"
                )
                or self._metadata.get(
                    "model"
                )
                or "edge_impulse",

            "source":
                "edge_impulse_serial",
            "signal_value":
                self._signals[-1]
                if self._signals
                else 0.0,
            "rms":
                self._rms(),
            "state":
                state,
            "alert":
                alert,
            "severity":
                severity,
            "rpm_raw":
                self._rpm_raw,
            "rpm_filtered":
                self._rpm_filtered,
            "rpm_pulses":
                self._rpm_pulses,
            "rpm_pulse_hz":
                self._rpm_pulse_hz,
            "temperature_c":
                self._temperature_c,
            "ntc_raw":
                self._ntc_raw,
            "ntc_voltage":
                self._ntc_voltage,
            "ntc_resistance":
                self._ntc_resistance,
        }

    def _rms(self) -> float:
        if not self._signals:
            return 0.0
        return math.sqrt(
            sum(
                value * value
                for value in self._signals
            )
            / len(self._signals)
        )

    def _flush_if_needed(self) -> None:
        elapsed = (
            monotonic()
            - self._last_flush
        )
        if (
            elapsed >=
            CSV_SAVE_INTERVAL_SECONDS
        ):
            self._flush_csv()

    def _flush_csv(self) -> None:
        if not self._sample_buffer:
            self._last_flush = monotonic()
            return
        
        self.csv_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        write_header = (
            not self.csv_path.exists()
            or self.csv_path.stat().st_size == 0
        )
        fieldnames = [
            "timestamp",
            "device_timestamp",
            "accel_x",
            "accel_y",
            "accel_z",
            "signal",
            "rpm_raw",
            "rpm_filtered",
            "temperature_c",
            "predicted_class",
            "confidence",
        ]

        with self.csv_path.open(
            "a",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )
            if write_header:
                writer.writeheader()
            writer.writerows(
                self._sample_buffer
            )

        self._sample_buffer.clear()

        self._last_flush = monotonic()

    @staticmethod
    def _float_or_none(
        value: str,
    ) -> float | None:
        try:
            return float(value)

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_or_none(
        value: str,
    ) -> int | None:
        try:
            return int(float(value))

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_label(
        value: str,
    ) -> str:
        normalized = unicodedata.normalize(
            "NFKD",
            value,
        )
        normalized = "".join(
            char
            for char in normalized
            if not unicodedata.combining(char)
        )
        return (
            normalized
            .strip()
            .lower()
            .replace("_", " ")
        )
    
    @classmethod
    def _state_from_class(
        cls,
        predicted_class: str,
    ) -> tuple[
        str,
        str | None,
        str | None,
    ]:
        label = cls._normalize_label(
            predicted_class
        )
        if "desligado" in label:
            return (
                "DESLIGADO",
                None,
                None,
            )
        if (
            "desbalanceamento pesado"
            in label
        ):
            return (
                "ANOMALIA",
                "Desbalanceamento pesado detectado",
                "CRITICAL",
            )
        if (
            "desbalanceamento leve"
            in label
        ):
            return (
                "ANOMALIA",
                "Desbalanceamento leve detectado",
                "WARNING",
            )
        if (
            "funcionamento normal"
            in label
            or label == "normal"
        ):
            return (
                "OPERANDO",
                None,
                None,
            )
        return (
            "OPERANDO",
            None,
            None,
        )
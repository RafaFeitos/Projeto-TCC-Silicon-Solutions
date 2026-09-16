from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DB = f"sqlite:///{ROOT_DIR / 'industrial_monitor.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass

class MachineRecord(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    machine_type: Mapped[str] = mapped_column(String(80), default="GENERIC")
    serial_port: Mapped[str | None] = mapped_column(String(40), nullable=True)
    baud: Mapped[int] = mapped_column(Integer, default=115200)
    ideal_cycle_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    good_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class InferenceRecord(Base):
    __tablename__ = "inferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), default=1, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    predicted_class: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(80))
    signal_value: Mapped[float] = mapped_column(Float)
    rms: Mapped[float] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(40))
    alert: Mapped[str | None] = mapped_column(String(160), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rpm_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpm_filtered: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpm_pulses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpm_pulse_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    ntc_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ntc_voltage: Mapped[float | None] = mapped_column(Float, nullable=True)
    ntc_resistance: Mapped[float | None] = mapped_column(Float, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_telemetry_columns()

def _ensure_telemetry_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    
    machine_columns = {
        "serial_port": "TEXT",
        "baud": "INTEGER NOT NULL DEFAULT 115200",
    }
    inference_columns = {
        "rpm_raw": "REAL",
        "rpm_filtered": "REAL",
        "rpm_pulses": "INTEGER",
        "rpm_pulse_hz": "REAL",
        "temperature_c": "REAL",
        "ntc_raw": "INTEGER",
        "ntc_voltage": "REAL",
        "ntc_resistance": "REAL",
    }

    with engine.begin() as connection:
        machine_existing = {
            row[1]
            for row in connection.exec_driver_sql(
                "PRAGMA table_info(machines)"
            )
        }

        for name, column_type in machine_columns.items():
            if name not in machine_existing:
                connection.exec_driver_sql(
                    f"ALTER TABLE machines ADD COLUMN {name} {column_type}"
                )
        inference_existing = {
            row[1]
            for row in connection.exec_driver_sql(
                "PRAGMA table_info(inferences)"
            )
        }
        for name, column_type in inference_columns.items():
            if name not in inference_existing:
                connection.exec_driver_sql(
                    f"ALTER TABLE inferences ADD COLUMN {name} {column_type}"
                )
                
def _machine_dict(row: MachineRecord) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "machine_type": row.machine_type,
        "serial_port": row.serial_port,
        "baud": row.baud,
        "ideal_cycle_time_seconds": row.ideal_cycle_time_seconds,
        "total_count": row.total_count,
        "good_count": row.good_count,
        "created_at": row.created_at,
    }


def ensure_default_machine() -> dict:
    with SessionLocal() as session:
        row = session.scalar(select(MachineRecord).order_by(MachineRecord.id).limit(1))

        if row is None:
            row = MachineRecord(name="Máquina 01")
            session.add(row)
            session.commit()
            session.refresh(row)

        return _machine_dict(row)


def list_machines() -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(select(MachineRecord).order_by(MachineRecord.id)).all()
        return [_machine_dict(row) for row in rows]


def get_machine(machine_id: int) -> dict | None:
    with SessionLocal() as session:
        row = session.get(MachineRecord, machine_id)
        return _machine_dict(row) if row else None


def create_machine(
    name: str | None,
    ideal_cycle_time_seconds: float | None = None,
    total_count: int = 0,
    good_count: int = 0,
) -> dict:
    with SessionLocal() as session:
        row = MachineRecord(
            name=(name or "").strip() or "Nova máquina",
            ideal_cycle_time_seconds=ideal_cycle_time_seconds,
            total_count=total_count,
            good_count=good_count,
        )

        session.add(row)
        session.flush()

        if not name or not name.strip():
            row.name = f"Máquina {row.id:02d}"

        session.commit()
        session.refresh(row)

        return _machine_dict(row)


def update_machine_production(
    machine_id: int,
    total_count: int,
    good_count: int,
    ideal_cycle_time_seconds: float | None = None,
) -> dict | None:
    with SessionLocal() as session:
        row = session.get(MachineRecord, machine_id)

        if row is None:
            return None

        row.total_count = total_count
        row.good_count = good_count

        if ideal_cycle_time_seconds is not None:
            row.ideal_cycle_time_seconds = ideal_cycle_time_seconds

        session.commit()
        session.refresh(row)

        return _machine_dict(row)


def persist_inference(item: dict) -> None:
    with SessionLocal() as session:
        session.add(InferenceRecord(**{k: item.get(k) for k in (
            "machine_id", "timestamp", "predicted_class", "confidence",
            "model_version", "source", "signal_value", "rms", "state", "alert", "severity", "rpm_raw", "rpm_filtered", "rpm_pulses", "rpm_pulse_hz", "temperature_c", "ntc_raw", "ntc_voltage", "ntc_resistance"
        )}))
        session.commit()

def list_inferences(machine_id: int, limit: int | None = None) -> list[InferenceRecord]:
    with SessionLocal() as session:
        rows = list(session.scalars(
            select(InferenceRecord)
            .where(InferenceRecord.machine_id == machine_id)
            .order_by(InferenceRecord.timestamp, InferenceRecord.id)
        ).all())

        return rows[-limit:] if limit else rows
    
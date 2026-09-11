from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DB = f"sqlite:///{ROOT_DIR / 'industrial_monitor.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class InferenceRecord(Base):
    __tablename__ = "inferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
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


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def persist_inference(item: dict) -> None:
    with SessionLocal() as session:
        session.add(InferenceRecord(**{k: item.get(k) for k in (
            "machine_id", "timestamp", "predicted_class", "confidence",
            "model_version", "source", "signal_value", "rms", "state", "alert", "severity"
        )}))
        session.commit()

from datetime import datetime
from pydantic import BaseModel, Field


class Inference(BaseModel):
    machine_id: int = 1
    timestamp: datetime
    predicted_class: str
    confidence: float = Field(ge=0, le=1)
    model_version: str
    source: str
    signal_value: float
    rms: float
    state: str
    alert: str | None = None
    severity: str | None = None


class DatasetInfo(BaseModel):
    file_name: str
    rows: int
    signal_column: str
    label_column: str | None
    timestamp_column: str | None
    columns: list[str]


class CurrentState(BaseModel):
    machine_id: int = 1
    machine_name: str
    state: str
    confidence: float
    predicted_class: str
    model_version: str
    source: str = "—"
    signal_value: float = 0.0
    rms: float = 0.0
    timestamp: datetime
    alert: str | None = None
    severity: str | None = None


class StreamStatus(BaseModel):
    running: bool
    cursor: int
    total: int
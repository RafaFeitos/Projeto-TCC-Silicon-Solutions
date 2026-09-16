from datetime import datetime
from pydantic import BaseModel, Field, model_validator


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

class MachineInfo(BaseModel):
    id: int
    name: str
    machine_type: str
    ideal_cycle_time_seconds: float | None = None
    total_count: int
    good_count: int
    created_at: datetime
    dataset_file: str


class MachineCreate(BaseModel):
    name: str | None = None
    ideal_cycle_time_seconds: float | None = Field(default=None, gt=0)
    total_count: int = Field(default=0, ge=0)
    good_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_counts(self):
        if self.good_count > self.total_count:
            raise ValueError("good_count não pode ser maior que total_count")
        return self


class ProductionUpdate(BaseModel):
    total_count: int = Field(ge=0)
    good_count: int = Field(ge=0)
    ideal_cycle_time_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_counts(self):
        if self.good_count > self.total_count:
            raise ValueError("good_count não pode ser maior que total_count")
        return self


class MachineMetrics(BaseModel):
    machine_id: int
    availability: float | None = None
    performance: float | None = None
    quality: float | None = None
    oee: float | None = None
    mtbf_hours: float | None = None
    operating_hours: float = 0.0
    downtime_hours: float = 0.0
    failure_count: int = 0
    total_count: int = 0
    good_count: int = 0
    ideal_cycle_time_seconds: float | None = None


class MachineSummary(BaseModel):
    machine: MachineInfo
    state: CurrentState | None = None
    metrics: MachineMetrics


class OverviewMetrics(BaseModel):
    oee: float | None = None
    mtbf_hours: float | None = None
    machine_count: int
    operating_count: int
    alert_count: int
    failure_count: int


class OverviewResponse(BaseModel):
    metrics: OverviewMetrics
    machines: list[MachineSummary]
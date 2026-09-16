export type Inference = {
  machine_id: number;
  timestamp: string;
  predicted_class: string;
  confidence: number;
  model_version: string;
  source: string;
  signal_value: number;
  rms: number;
  state: string;
  alert?: string | null;
  severity?: string | null;
  rpm_raw?: number | null;
  rpm_filtered?: number | null;
  rpm_pulses?: number | null;
  rpm_pulse_hz?: number | null;
  temperature_c?: number | null;
  ntc_raw?: number | null;
  ntc_voltage?: number | null;
  ntc_resistance?: number | null;
};

export type DatasetInfo = {
  file_name: string;
  rows: number;
  signal_column: string;
  label_column?: string | null;
  timestamp_column?: string | null;
  columns: string[];
};

export type CurrentState = Inference & {
  machine_name: string;
};

export type MachineInfo = {
  id: number;
  name: string;
  machine_type: string;
  ideal_cycle_time_seconds: number | null;
  total_count: number;
  good_count: number;
  created_at: string;
  dataset_file: string;
};

export type MachineCreate = {
  name?: string | null;
  ideal_cycle_time_seconds?: number | null;
  total_count: number;
  good_count: number;
};

export type ProductionUpdate = {
  ideal_cycle_time_seconds?: number | null;
  total_count: number;
  good_count: number;
};

export type MachineMetrics = {
  machine_id: number;
  availability: number | null;
  performance: number | null;
  quality: number | null;
  oee: number | null;
  mtbf_hours: number | null;
  operating_hours: number;
  downtime_hours: number;
  failure_count: number;
  total_count: number;
  good_count: number;
  ideal_cycle_time_seconds: number | null;
};

export type MachineSummary = {
  machine: MachineInfo;
  state: CurrentState | null;
  metrics: MachineMetrics;
};

export type OverviewMetrics = {
  oee: number | null;
  mtbf_hours: number | null;
  machine_count: number;
  operating_count: number;
  alert_count: number;
  failure_count: number;
};

export type OverviewResponse = {
  metrics: OverviewMetrics;
  machines: MachineSummary[];
};

export type StreamStatus = {
  running: boolean;
  cursor: number;
  total: number;
};
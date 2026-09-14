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
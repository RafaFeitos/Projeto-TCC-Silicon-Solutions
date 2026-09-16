from pathlib import Path
import os
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
BACKEND_DIR = ROOT_DIR / "backend"

load_dotenv(BACKEND_DIR / ".env")
DATA_DIR.mkdir(parents=True, exist_ok=True)

SERIAL_PORT = os.getenv("SERIAL_PORT", "auto").strip()
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))
SERIAL_RECONNECT_SECONDS = float(os.getenv("SERIAL_RECONNECT_SECONDS", "2.0"))
SERIAL_WINDOW_SAMPLES = int(os.getenv("SERIAL_WINDOW_SAMPLES", "100"))
CSV_SAVE_INTERVAL_SECONDS = float(os.getenv("CSV_SAVE_INTERVAL_SECONDS", "10"))
MONITOR_MODE = os.getenv("MONITOR_MODE", "replay",).strip().lower()
RMS_WARNING = float(os.getenv("RMS_WARNING", "0.35"))
RMS_CRITICAL = float(os.getenv("RMS_CRITICAL", "0.75"))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "32"))
REPLAY_DELAY_SECONDS = float(os.getenv("REPLAY_DELAY_SECONDS", "0.35"))
METRIC_MAX_GAP_SECONDS = float(os.getenv("METRIC_MAX_GAP_SECONDS", "60"))

DEMO_DATASET_PATH = DATA_DIR / os.getenv("DEMO_DATASET_FILE", "maquina_demo.csv")

def machine_csv_path(machine_id: int) -> Path:
    return DATA_DIR / f"maquina_{machine_id:02d}.csv"
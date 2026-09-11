from pathlib import Path
import os 

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"

RMS_WARNING = float(os.getenv("RMS_WARNING", "0.35"))
RMS_CRITICAL = float(os.getenv("RMS_CRITICAL", "0.75"))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "32"))
REPLAY_DELAY_SECONDS = float(os.getenv("REPLAY_DELAY_SECONDS", "0.35"))
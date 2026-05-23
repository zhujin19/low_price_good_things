from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_SQLITE_DB = PROJECT_ROOT / "flight_monitor.db"

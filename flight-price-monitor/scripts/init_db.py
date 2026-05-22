from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import Base, engine  # noqa: E402
import app.models  # noqa: F401,E402


if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)
    print('DB initialized')

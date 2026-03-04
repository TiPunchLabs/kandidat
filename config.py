import os
from pathlib import Path

# Data directory: contains candidatures/, kandidat.db, etc.
# Priority: FT_DATA_DIR (explicit override) > KANDIDAT_ENV (dev/prod) > default (prod)
_project_root = Path(__file__).resolve().parent
_env = os.environ.get("KANDIDAT_ENV", "prod")
_default_data_dir = str(_project_root / "data" / _env)

FT_DATA_DIR = os.environ.get("FT_DATA_DIR", _default_data_dir)

# Database URL: when set, use PostgreSQL; when absent, fall back to SQLite
DATABASE_URL = os.environ.get("DATABASE_URL")

import os
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def database_path() -> Path:
    directory = Path(os.environ.get('PDF_LEARNING_DATA_DIR', 'data')).expanduser()
    if not directory.is_absolute():
        directory = REPOSITORY_ROOT / directory
    return directory.resolve() / 'learning_os.sqlite3'

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import database_path
from app.db.connection import create_database_engine, ping_database
from app.main import create_app


def test_creates_and_reopens_database(tmp_path):
    path = tmp_path / 'nested' / 'learning_os.sqlite3'
    engine = create_database_engine(path)
    try:
        ping_database(engine)
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()
    assert path.is_file()
    identity = path.stat().st_ino
    engine = create_database_engine(path)
    try:
        ping_database(engine)
        assert path.stat().st_ino == identity
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()


def test_restart_reuses_database():
    for _ in range(2):
        with TestClient(create_app()) as client:
            assert client.get('/health').status_code == 200
        assert database_path().is_file()


def test_default_path_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv('PDF_LEARNING_DATA_DIR')
    monkeypatch.setattr('app.config.REPOSITORY_ROOT', tmp_path / 'repo')
    monkeypatch.chdir(tmp_path)
    assert database_path() == tmp_path / 'repo/data/learning_os.sqlite3'


def test_relative_override(tmp_path, monkeypatch):
    monkeypatch.setattr('app.config.REPOSITORY_ROOT', tmp_path)
    monkeypatch.setenv('PDF_LEARNING_DATA_DIR', 'custom/storage')
    assert database_path() == tmp_path / 'custom/storage/learning_os.sqlite3'


def test_absolute_override(tmp_path, monkeypatch):
    monkeypatch.setenv('PDF_LEARNING_DATA_DIR', str(tmp_path))
    assert database_path() == tmp_path / 'learning_os.sqlite3'


def test_home_expansion(tmp_path, monkeypatch):
    # Path.expanduser delegates to os.path.expanduser; patch it without changing HOME.
    monkeypatch.setattr('os.path.expanduser', lambda value: str(tmp_path / value[2:]))
    monkeypatch.setenv('PDF_LEARNING_DATA_DIR', '~/learning-data')
    assert database_path() == tmp_path / 'learning-data/learning_os.sqlite3'

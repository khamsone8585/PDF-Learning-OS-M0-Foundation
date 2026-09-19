import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_data_directory(tmp_path, monkeypatch):
    monkeypatch.setenv('PDF_LEARNING_DATA_DIR', str(tmp_path / 'data'))
    import tempfile
    spool = tmp_path / 'spools'
    spool.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(spool))


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def migrated():
    from alembic import command
    from app.db.migrations import migration_config
    command.upgrade(migration_config(), 'head')


@pytest.fixture
def library_client(migrated):
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def pdf_bytes():
    import pymupdf
    with pymupdf.open() as document:
        document.new_page()
        document.set_metadata({'title': 'Embedded title', 'author': 'Embedded author'})
        return document.tobytes()

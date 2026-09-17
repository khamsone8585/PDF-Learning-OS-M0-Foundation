import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_data_directory(tmp_path, monkeypatch):
    monkeypatch.setenv('PDF_LEARNING_DATA_DIR', str(tmp_path / 'data'))


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client

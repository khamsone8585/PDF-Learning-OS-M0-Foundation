import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import create_app


def test_health_success(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'ok'}


def test_initialization_failure(monkeypatch):
    def fail(*args):
        raise PermissionError('/private/learner/data')

    monkeypatch.setattr('app.main.create_database_engine', fail)
    with TestClient(create_app()) as client:
        response = client.get('/health')
    assert response.status_code == 503
    assert response.json() == {'status': 'error', 'database': 'unavailable'}


def test_query_failure(client, monkeypatch):
    def fail(*args):
        raise OperationalError('SELECT private', {}, Exception('/private/data'))

    monkeypatch.setattr('app.api.health.ping_database', fail)
    response = client.get('/health')
    assert response.status_code == 503
    assert response.json() == {'status': 'error', 'database': 'unavailable'}


def test_connection_failure(tmp_path, monkeypatch):
    # A directory cannot be opened as a SQLite database file.
    path = tmp_path / 'blocked'
    (path / 'learning_os.sqlite3').mkdir(parents=True)
    monkeypatch.setenv('PDF_LEARNING_DATA_DIR', str(path))
    with TestClient(create_app()) as client:
        response = client.get('/health')
    assert response.status_code == 503
    assert response.json() == {'status': 'error', 'database': 'unavailable'}


@pytest.mark.parametrize('origin', ['http://localhost:5173', 'http://127.0.0.1:5173'])
def test_allowed_origin(client, origin):
    response = client.get('/health', headers={'Origin': origin})
    assert response.headers['access-control-allow-origin'] == origin
    assert 'access-control-allow-credentials' not in response.headers
    preflight = client.options('/health', headers={
        'Origin': origin, 'Access-Control-Request-Method': 'GET',
    })
    assert preflight.status_code == 200
    assert preflight.headers['access-control-allow-origin'] == origin


def test_disallowed_origin(client):
    headers = {'Origin': 'https://unrelated.example'}
    assert 'access-control-allow-origin' not in client.get('/health', headers=headers).headers
    headers['Access-Control-Request-Method'] = 'GET'
    response = client.options('/health', headers=headers)
    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers

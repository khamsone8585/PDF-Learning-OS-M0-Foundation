from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pymupdf
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.config import database_path
from app.db.connection import create_database_engine
from app.db.migrations import migration_config, schema_ready
from app.main import create_app
from app.models.book import Book
from app.services.library_storage import DataLock


def upload(client, data, name='book.pdf', fields=None):
    return client.post('/books', files={'file': (name, data, 'application/pdf')}, data=fields or {})


def root():
    return database_path().parent


def fail(*args, **kwargs):
    raise OSError('private failure')


def assert_empty(client):
    assert client.get('/books').json() == {'books': []}
    assert list((root() / 'books').iterdir()) == []
    assert list((root() / '.staging').iterdir()) == []


def test_import_metadata_bytes_list_details(library_client, pdf_bytes):
    response = upload(library_client, pdf_bytes, fields={'title': ' Manual ', 'edition': '2', 'year': '2020'})
    assert response.status_code == 201, response.text
    book = response.json()
    assert book['title'] == 'Manual' and book['author'] == 'Embedded author'
    assert book['edition'] == '2' and book['year'] == 2020
    assert book['page_count'] == 1 and book['imported_at'].endswith('Z')
    assert book['size_bytes'] == len(pdf_bytes) and book['file_available']
    assert 'sha256' not in book and 'path' not in book
    assert response.headers['location'] == '/books/' + book['id']
    assert (root() / 'books' / book['id'] / 'original.pdf').read_bytes() == pdf_bytes
    assert library_client.get(response.headers['location']).json() == book
    assert library_client.get('/books').json() == {'books': [book]}


def test_restart(migrated, pdf_bytes):
    with TestClient(create_app()) as client:
        book = upload(client, pdf_bytes).json()
    with TestClient(create_app()) as client:
        assert client.get('/books/' + book['id']).json() == book


def test_metadata_fallback_and_filename(library_client):
    with pymupdf.open() as doc:
        doc.new_page()
        data = doc.tobytes()
    book = upload(library_client, data, '../folder\\cafe\u0301.pdf').json()
    assert book['original_filename'] == 'café.pdf' and book['title'] == 'café'
    assert book['author'] is None and book['edition'] is None and book['year'] is None


def test_duplicate_and_filename_collision(library_client, pdf_bytes):
    first = upload(library_client, pdf_bytes).json()
    for name in ('book.pdf', 'renamed.pdf'):
        duplicate = upload(library_client, pdf_bytes, name)
        assert duplicate.status_code == 409
        assert duplicate.json()['error']['existing_book_id'] == first['id']
    with pymupdf.open(stream=pdf_bytes) as doc:
        doc.new_page()
        second = upload(library_client, doc.tobytes()).json()
    assert second['id'] != first['id']
    assert [b['id'] for b in library_client.get('/books').json()['books']] == [second['id'], first['id']]
    assert len(list((root() / 'books').iterdir())) == 2


def test_concurrent_duplicate(library_client, pdf_bytes):
    with ThreadPoolExecutor(2) as pool:
        statuses = list(pool.map(lambda _: upload(library_client, pdf_bytes).status_code, range(2)))
    assert sorted(statuses) == [201, 409]


@pytest.mark.parametrize('data', [b'', b'not a pdf', b'%PDF-1.7\nbroken'])
def test_invalid_pdf_cleanup(library_client, data):
    assert upload(library_client, data).status_code == 422
    assert_empty(library_client)


@pytest.mark.parametrize('password', ['', 'secret'])
def test_encrypted(library_client, password):
    with pymupdf.open() as doc:
        doc.new_page()
        data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw=password)
    response = upload(library_client, data)
    assert response.status_code == 422 and response.json()['error']['code'] == 'encrypted_pdf'
    assert_empty(library_client)


@pytest.mark.parametrize('fields', [{'year': '0'}, {'year': '10000'}, {'year': '1.2'}, {'title': 'a'*501}, {'edition': 'x'*101}, {'extra': 'x'}])
def test_invalid_fields(library_client, pdf_bytes, fields):
    assert upload(library_client, pdf_bytes, fields=fields).status_code == 422
    assert_empty(library_client)


def test_transport_errors(library_client, pdf_bytes):
    assert library_client.post('/books', json={}).status_code == 415
    assert library_client.post('/books', files={'other': ('x', pdf_bytes)}).status_code == 422
    assert library_client.post('/books', files=[('file', ('a', pdf_bytes)), ('file', ('b', pdf_bytes))]).status_code == 422
    assert library_client.post('/books', content=b'x', headers={'Content-Type': 'multipart/form-data'}).status_code == 400
    assert library_client.get('/books/not-a-uuid').status_code == 422
    assert library_client.get('/books/' + str(uuid4())).status_code == 404


def test_size_boundaries(library_client, pdf_bytes, monkeypatch):
    monkeypatch.setattr('app.services.library.MAX_FILE_BYTES', len(pdf_bytes))
    assert upload(library_client, pdf_bytes).status_code == 201
    assert upload(library_client, pdf_bytes + b' ').status_code == 413
    assert list((root() / '.staging').iterdir()) == []


def test_request_limit(library_client, pdf_bytes, monkeypatch):
    monkeypatch.setattr('app.api.body_limit.MAX_REQUEST_BYTES', 10)
    assert upload(library_client, pdf_bytes).status_code == 413
    assert_empty(library_client)


def test_delete_and_missing_file(library_client, pdf_bytes):
    for missing in (False, True):
        book = upload(library_client, pdf_bytes).json()
        if missing:
            (root() / 'books' / book['id'] / 'original.pdf').unlink()
            assert not library_client.get('/books/' + book['id']).json()['file_available']
        assert library_client.delete('/books/' + book['id']).status_code == 204
        assert library_client.delete('/books/' + book['id']).status_code == 404
        assert_empty(library_client)
        assert list((root() / '.trash').iterdir()) == []


def test_no_schema_and_migrations(client):
    assert client.get('/health').status_code == 200
    assert client.get('/books').json()['error']['code'] == 'library_setup_required'
    with pytest.raises(BlockingIOError):
        command.upgrade(migration_config(), 'head')


def test_migration_upgrade_and_constraints():
    engine = create_database_engine(database_path())
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    identity = database_path().stat().st_ino
    command.upgrade(migration_config(), 'head')
    command.upgrade(migration_config(), 'head')
    assert schema_ready(engine)
    assert database_path().stat().st_ino == identity
    assert sorted(inspect(engine).get_table_names()) == ['alembic_version', 'books']
    assert len(inspect(engine).get_check_constraints('books')) == 8
    engine.dispose()


def test_single_process(library_client):
    with pytest.raises(BlockingIOError):
        DataLock(root())
    with TestClient(create_app()) as other:
        assert other.get('/books').status_code == 503
    assert library_client.get('/books').status_code == 200


def test_uuid_collision_does_not_remove_existing(library_client, pdf_bytes, monkeypatch):
    book = upload(library_client, pdf_bytes).json()
    monkeypatch.setattr('app.services.library.uuid4', lambda: book['id'])
    assert upload(library_client, pdf_bytes).status_code == 503
    assert (root() / 'books' / book['id'] / 'original.pdf').read_bytes() == pdf_bytes


def test_symlink_refuses_delete(library_client, pdf_bytes, tmp_path):
    book = upload(library_client, pdf_bytes).json()
    pdf = root() / 'books' / book['id'] / 'original.pdf'
    pdf.unlink()
    external = tmp_path / 'outside.pdf'; external.write_bytes(pdf_bytes)
    pdf.symlink_to(external)
    assert library_client.delete('/books/' + book['id']).status_code == 503
    assert external.read_bytes() == pdf_bytes
    with Session(library_client.app.state.database_engine) as session:
        assert session.get(Book, book['id']) is not None


@pytest.mark.parametrize('phase', ['flush', 'commit'])
def test_import_db_failure_cleanup(library_client, pdf_bytes, monkeypatch, phase):
    with monkeypatch.context() as patch:
        patch.setattr(Session, phase, fail)
        response = upload(library_client, pdf_bytes)
        assert response.status_code == 503
        assert 'private' not in response.text
    assert_empty(library_client)


def test_import_commit_succeeded_then_failed(library_client, pdf_bytes, monkeypatch):
    commit = Session.commit
    def uncertain(session):
        commit(session)
        raise OSError('lost acknowledgement')
    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', uncertain)
        assert upload(library_client, pdf_bytes).status_code == 503
    books = library_client.get('/books').json()['books']
    assert len(books) == 1 and books[0]['file_available']
    assert upload(library_client, pdf_bytes).status_code == 409


def test_move_failure_cleanup(library_client, pdf_bytes, monkeypatch):
    service = library_client.app.state.library
    with monkeypatch.context() as patch:
        patch.setattr(service.storage, 'move', fail)
        assert upload(library_client, pdf_bytes).status_code == 503
    assert_empty(library_client)


def test_delete_rollback_restores(library_client, pdf_bytes, monkeypatch):
    book = upload(library_client, pdf_bytes).json()
    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', fail)
        assert library_client.delete('/books/' + book['id']).status_code == 503
    assert library_client.get('/books/' + book['id']).json()['file_available']
    assert list((root() / '.trash').iterdir()) == []


def test_cleanup_pending_retry(library_client, pdf_bytes, monkeypatch):
    book = upload(library_client, pdf_bytes).json()
    service = library_client.app.state.library
    with monkeypatch.context() as patch:
        patch.setattr(service.storage, 'remove', fail)
        response = library_client.delete('/books/' + book['id'])
        assert response.json()['error']['code'] == 'deletion_cleanup_pending'
        assert service.blocked
    assert library_client.delete('/books/' + book['id']).status_code == 204
    assert_empty(library_client)


def test_startup_recovery(migrated, pdf_bytes):
    with TestClient(create_app()) as client:
        book = upload(client, pdf_bytes).json()
    (root() / 'books' / book['id']).rename(root() / '.trash' / book['id'])
    for area in ('books', '.staging', '.trash'):
        path = root() / area / str(uuid4()); path.mkdir(); (path / 'original.pdf').write_bytes(pdf_bytes)
    with TestClient(create_app()) as client:
        assert client.get('/books/' + book['id']).json()['file_available']
        assert len(list((root() / 'books').iterdir())) == 1
        assert list((root() / '.staging').iterdir()) == list((root() / '.trash').iterdir()) == []


def test_recovery_unknown_entry_no_cleanup(migrated, pdf_bytes):
    with TestClient(create_app()):
        pass
    stage = root() / '.staging' / str(uuid4()); stage.mkdir(); (stage / 'original.pdf').write_bytes(pdf_bytes)
    (root() / 'books' / 'unexpected').mkdir()
    with TestClient(create_app()) as client:
        assert client.get('/books').status_code == 503
    assert stage.exists()


def test_mutation_cors(library_client):
    for method in ('POST', 'DELETE'):
        response = library_client.options('/books', headers={
            'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': method})
        assert response.status_code == 200

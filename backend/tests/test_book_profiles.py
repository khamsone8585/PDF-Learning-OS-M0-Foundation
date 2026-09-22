from uuid import uuid4

import pymupdf
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.config import database_path
from app.db.connection import create_database_engine
from app.db.migrations import migration_config
from app.main import create_app


def pdf(label='profile book'):
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), label)
        return document.tobytes()


def book(client):
    response = client.post('/books', files={
        'file': ('profile.pdf', pdf(), 'application/pdf')})
    assert response.status_code == 201, response.text
    return response.json()


def body(**changes):
    value = {
        'domain': ' Computer science ',
        'difficulty': 'intermediate',
        'prerequisites': [' Programming basics ', 'Discrete math'],
        'main_topics': ['Algorithms', 'Data structures'],
        'orientation': 'balanced',
        'strengths': ['Clear examples'],
        'weaknesses': ['Limited exercises'],
        'suggested_use': ' Use as a primary introduction. ',
    }
    value.update(changes)
    return value


def test_absent_profile_and_missing_book(library_client):
    item = book(library_client)
    assert library_client.get(f"/books/{item['id']}/profile").json() == {'profile': None}
    response = library_client.get(f'/books/{uuid4()}/profile')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'book_not_found'
    assert library_client.get('/books/not-a-uuid/profile').status_code == 422


def test_create_read_and_replace_profile(library_client):
    item = book(library_client)
    response = library_client.put(f"/books/{item['id']}/profile", json=body())
    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile['domain'] == 'Computer science'
    assert profile['prerequisites'] == ['Programming basics', 'Discrete math']
    assert profile['suggested_use'] == 'Use as a primary introduction.'
    assert set(profile['provenance'].values()) == {'manual'}
    assert profile['created_at'] == profile['updated_at']
    assert library_client.get(f"/books/{item['id']}/profile").json() == {'profile': profile}

    replacement = body(domain=None, prerequisites=[], strengths=[], weaknesses=[],
                       suggested_use=None, difficulty='advanced', orientation='theory_heavy')
    changed = library_client.put(f"/books/{item['id']}/profile", json=replacement).json()
    assert changed['created_at'] == profile['created_at']
    assert changed['updated_at'] >= profile['updated_at']
    assert changed['domain'] is None and changed['prerequisites'] == []
    assert changed['provenance']['domain'] is None
    assert changed['provenance']['prerequisites'] is None
    assert changed['provenance']['difficulty'] == 'manual'
    engine = library_client.app.state.database_engine
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM book_profiles')) == 1
        assert connection.scalar(text(
            'SELECT prerequisites_json FROM book_profiles WHERE book_id=:id'), {'id': item['id']}) == '[]'


@pytest.mark.parametrize(('changes', 'code'), [
    ({'domain': ' ', 'difficulty': None, 'prerequisites': [], 'main_topics': [],
      'orientation': None, 'strengths': [], 'weaknesses': [], 'suggested_use': ' '},
     'empty_book_profile'),
    ({'domain': 'x' * 201}, 'invalid_domain'),
    ({'suggested_use': 'x' * 2001}, 'invalid_suggested_use'),
    ({'prerequisites': ['']}, 'invalid_prerequisites'),
    ({'prerequisites': ['Python', 'python']}, 'duplicate_prerequisites'),
    ({'prerequisites': [str(index) for index in range(26)]}, 'invalid_prerequisites'),
    ({'main_topics': ['x' * 201]}, 'invalid_main_topics'),
    ({'strengths': ['x' * 501]}, 'invalid_strengths'),
    ({'weaknesses': [str(index) for index in range(21)]}, 'invalid_weaknesses'),
])
def test_structured_validation_is_atomic(library_client, changes, code):
    item = book(library_client)
    response = library_client.put(f"/books/{item['id']}/profile", json=body(**changes))
    assert response.status_code == 422
    assert response.json()['error']['code'] == code
    assert library_client.get(f"/books/{item['id']}/profile").json() == {'profile': None}


def test_schema_rejects_enums_missing_fields_and_client_provenance(library_client):
    item = book(library_client)
    for value in [body(difficulty='expert'), body(orientation='mixed')]:
        assert library_client.put(f"/books/{item['id']}/profile", json=value).status_code == 422
    incomplete = body()
    del incomplete['domain']
    assert library_client.put(f"/books/{item['id']}/profile", json=incomplete).status_code == 422
    assert library_client.put(f"/books/{item['id']}/profile",
                              json={**body(), 'provenance': {'domain': 'derived'}}).status_code == 422


def test_profile_persists_restart_and_does_not_require_pdf_or_processing(migrated):
    with TestClient(create_app()) as client:
        item = book(client)
        root = database_path().parent
        (root / 'books' / item['id'] / 'original.pdf').unlink()
        saved = client.put(f"/books/{item['id']}/profile", json=body()).json()
    with TestClient(create_app()) as client:
        assert client.get(f"/books/{item['id']}/profile").json() == {'profile': saved}


@pytest.mark.parametrize('status', ['unprocessed', 'processed', 'failed'])
def test_processing_status_does_not_gate_profiles(library_client, status):
    item = book(library_client)
    with library_client.app.state.database_engine.begin() as connection:
        connection.execute(text('UPDATE books SET processing_status=:status WHERE id=:id'),
                           {'status': status, 'id': item['id']})
    assert library_client.put(f"/books/{item['id']}/profile", json=body()).status_code == 200


def test_delete_cascades_profile(library_client):
    item = book(library_client)
    assert library_client.put(f"/books/{item['id']}/profile", json=body()).status_code == 200
    assert library_client.delete(f"/books/{item['id']}").status_code == 204
    with library_client.app.state.database_engine.connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM book_profiles')) == 0


def test_upgrade_populated_m3_preserves_existing_data():
    command.upgrade(migration_config(), '0003_learning_goals')
    engine = create_database_engine(database_path())
    book_ids = [str(uuid4()) for _ in range(3)]
    goal_id = str(uuid4())
    root = database_path().parent
    original = root / 'books' / book_ids[0] / 'original.pdf'
    page_artifact = root / 'books' / book_ids[0] / 'extracted' / 'generation' / 'pages' / '000001.txt'
    original.parent.mkdir(parents=True)
    page_artifact.parent.mkdir(parents=True)
    original.write_bytes(b'original bytes')
    page_artifact.write_bytes(b'exact page text')
    with engine.begin() as connection:
        for index, book_id in enumerate(book_ids):
            connection.execute(text("""INSERT INTO books
                (id,title,original_filename,author,edition,year,page_count,imported_at,sha256,size_bytes,
                 processing_status,processing_error_code,processing_error_message,processing_started_at,
                 processed_at,active_extraction_id,toc_status)
                VALUES (:id,:title,:filename,NULL,NULL,NULL,1,'2026-09-22T00:00:00Z',:sha,10,
                        'unprocessed',NULL,NULL,NULL,NULL,NULL,NULL)"""),
                {'id': book_id, 'title': f'Book {index}', 'filename': f'{index}.pdf',
                 'sha': f'{index + 1:x}' * 64})
        connection.execute(text("INSERT INTO learning_goals VALUES (:id,'Goal',NULL,1,:at,:at)"),
                           {'id': goal_id, 'at': '2026-09-22T00:00:00Z'})
        for book_id in book_ids:
            connection.execute(text('INSERT INTO learning_goal_books VALUES (:goal,:book)'),
                               {'goal': goal_id, 'book': book_id})
        connection.execute(text("INSERT INTO pages VALUES (:book,1,15,:sha)"),
                           {'book': book_ids[0], 'sha': 'a' * 64})
        connection.execute(text("INSERT INTO chapters VALUES (:id,:book,0,'Full document',1,1,1,'fallback')"),
                           {'id': str(uuid4()), 'book': book_ids[0]})
    engine.dispose()
    command.upgrade(migration_config(), 'head')
    engine = create_database_engine(database_path())
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM books')) == 3
        assert connection.scalar(text('SELECT count(*) FROM learning_goals')) == 1
        assert connection.scalar(text('SELECT count(*) FROM learning_goal_books')) == 3
        assert connection.scalar(text('SELECT count(*) FROM pages')) == 1
        assert connection.scalar(text('SELECT count(*) FROM chapters')) == 1
        assert connection.scalar(text('SELECT count(*) FROM book_profiles')) == 0
        assert 'book_profiles' in inspect(engine).get_table_names()
        assert original.read_bytes() == b'original bytes'
        assert page_artifact.read_bytes() == b'exact page text'
    engine.dispose()

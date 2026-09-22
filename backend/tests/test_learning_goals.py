from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pymupdf
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import database_path
from app.db.connection import create_database_engine
from app.db.migrations import migration_config
from app.main import create_app
from app.models.learning_goal import LearningGoal, LearningGoalBook


def pdf(label):
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), label)
        return document.tobytes()


def books(client, count=6):
    result = []
    for index in range(count):
        response = client.post('/books', files={
            'file': (f'book-{index}.pdf', pdf(f'book {index}'), 'application/pdf')})
        assert response.status_code == 201, response.text
        result.append(response.json())
    return result


def create(client, ids, title='Learn systems', description=' Build durable foundations. '):
    return client.post('/learning-goals', json={
        'title': title, 'description': description, 'book_ids': ids})


def test_empty_active_goal(library_client):
    assert library_client.get('/learning-goals/active').json() == {'goal': None}


@pytest.mark.parametrize('count', [3, 5])
def test_create_goal_with_valid_book_count(library_client, count):
    selected = books(library_client, count)
    response = create(library_client, [book['id'] for book in selected])
    assert response.status_code == 201, response.text
    goal = response.json()
    assert goal['title'] == 'Learn systems'
    assert goal['description'] == 'Build durable foundations.'
    assert goal['is_active'] is True
    assert goal['book_ids'] == sorted(book['id'] for book in selected)
    assert goal['created_at'].endswith('Z') and goal['updated_at'] == goal['created_at']
    assert response.headers['location'] == '/learning-goals/' + goal['id']
    assert library_client.get('/learning-goals/active').json() == {'goal': goal}


@pytest.mark.parametrize('count', [0, 1, 2, 6])
def test_rejects_invalid_book_count(library_client, count):
    selected = books(library_client, count) if count else []
    response = create(library_client, [book['id'] for book in selected])
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'invalid_book_selection'
    assert library_client.get('/learning-goals/active').json() == {'goal': None}


def test_rejects_invalid_text_duplicate_and_missing_ids(library_client):
    selected = books(library_client, 3)
    ids = [book['id'] for book in selected]
    cases = [
        ({'title': ' ', 'description': None, 'book_ids': ids}, 'invalid_goal_title'),
        ({'title': 'x' * 201, 'description': None, 'book_ids': ids}, 'invalid_goal_title'),
        ({'title': 'Goal', 'description': 'x' * 2001, 'book_ids': ids}, 'invalid_goal_description'),
        ({'title': 'Goal', 'description': None, 'book_ids': [ids[0], ids[0], ids[1]]},
         'duplicate_book_ids'),
        ({'title': 'Goal', 'description': None, 'book_ids': [ids[0], ids[1], 'bad']},
         'invalid_book_id'),
    ]
    for body, code in cases:
        response = library_client.post('/learning-goals', json=body)
        assert response.status_code == 422 and response.json()['error']['code'] == code
    missing = str(uuid4())
    response = create(library_client, [ids[0], ids[1], missing])
    assert response.status_code == 404
    assert response.json()['error'] == {
        'code': 'books_not_found', 'message': 'One or more selected books were not found.',
        'missing_book_ids': [missing]}
    assert library_client.get('/learning-goals/active').json() == {'goal': None}


def test_blank_description_and_processing_state_are_irrelevant(library_client):
    selected = books(library_client, 3)
    engine = library_client.app.state.database_engine
    with engine.begin() as connection:
        connection.execute(text("UPDATE books SET processing_status='failed' WHERE id=:id"),
                           {'id': selected[0]['id']})
        connection.execute(text("UPDATE books SET processing_status='processed' WHERE id=:id"),
                           {'id': selected[1]['id']})
    response = create(library_client, [book['id'] for book in selected], description='   ')
    assert response.status_code == 201
    assert response.json()['description'] is None


def test_new_goal_deactivates_previous_and_failed_create_rolls_back(library_client, monkeypatch):
    selected = books(library_client, 6)
    first = create(library_client, [book['id'] for book in selected[:3]], title='First').json()
    second = create(library_client, [book['id'] for book in selected[3:]], title='Second').json()
    assert library_client.get('/learning-goals/active').json()['goal']['id'] == second['id']
    with Session(library_client.app.state.database_engine) as session:
        assert session.get(LearningGoal, first['id']).is_active is False
        assert session.get(LearningGoal, second['id']).is_active is True

    def fail(_session):
        raise OSError('private failure')

    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', fail)
        response = create(library_client, [book['id'] for book in selected[:3]], title='Third')
        assert response.status_code == 503 and 'private' not in response.text
    assert library_client.get('/learning-goals/active').json()['goal']['id'] == second['id']


def test_replace_books_and_reject_inactive_or_missing_goal(library_client):
    selected = books(library_client, 6)
    first = create(library_client, [book['id'] for book in selected[:3]], title='First').json()
    second = create(library_client, [book['id'] for book in selected[3:]], title='Second').json()
    replacement = [selected[0]['id'], selected[2]['id'], selected[4]['id']]
    response = library_client.put(f"/learning-goals/{second['id']}/books",
                                  json={'book_ids': replacement})
    assert response.status_code == 200
    assert response.json()['book_ids'] == sorted(replacement)
    assert response.json()['updated_at'] >= second['updated_at']
    assert library_client.put(f"/learning-goals/{first['id']}/books",
                              json={'book_ids': replacement}).status_code == 409
    assert library_client.put(f'/learning-goals/{uuid4()}/books',
                              json={'book_ids': replacement}).status_code == 404
    assert library_client.put('/learning-goals/not-a-uuid/books',
                              json={'book_ids': replacement}).status_code == 422


def test_restart_persists_active_goal(migrated):
    with TestClient(create_app()) as client:
        selected = books(client, 3)
        goal = create(client, [book['id'] for book in selected]).json()
    with TestClient(create_app()) as client:
        assert client.get('/learning-goals/active').json() == {'goal': goal}


def test_active_selection_blocks_delete_until_replaced(library_client):
    selected = books(library_client, 4)
    ids = [book['id'] for book in selected]
    goal = create(library_client, ids[:3]).json()
    root = database_path().parent
    response = library_client.delete('/books/' + ids[0])
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'book_in_active_goal'
    assert (root / 'books' / ids[0] / 'original.pdf').is_file()
    assert library_client.get('/books/' + ids[0]).status_code == 200

    assert library_client.put(f"/learning-goals/{goal['id']}/books",
                              json={'book_ids': ids[1:]}).status_code == 200
    assert library_client.delete('/books/' + ids[0]).status_code == 204


def test_inactive_association_cascades_on_book_delete(library_client):
    selected = books(library_client, 6)
    ids = [book['id'] for book in selected]
    first = create(library_client, ids[:3], title='First').json()
    create(library_client, ids[3:], title='Second')
    assert library_client.delete('/books/' + ids[0]).status_code == 204
    with Session(library_client.app.state.database_engine) as session:
        assert session.get(LearningGoalBook, (first['id'], ids[0])) is None


def test_concurrent_creation_leaves_one_active_goal(library_client):
    selected = books(library_client, 6)
    groups = [[book['id'] for book in selected[:3]], [book['id'] for book in selected[3:]]]
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda item: create(library_client, item[1], title=item[0]),
                                  [('First', groups[0]), ('Second', groups[1])]))
    assert [response.status_code for response in responses] == [201, 201]
    with Session(library_client.app.state.database_engine) as session:
        assert len(list(session.scalars(select(LearningGoal).where(
            LearningGoal.is_active.is_(True))))) == 1


def test_upgrade_from_populated_m2_preserves_data():
    command.upgrade(migration_config(), '0002_pdf_processing')
    engine = create_database_engine(database_path())
    book_id, chapter_id = str(uuid4()), str(uuid4())
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO books
            (id,title,original_filename,author,edition,year,page_count,imported_at,sha256,size_bytes,
             processing_status,processing_error_code,processing_error_message,processing_started_at,
             processed_at,active_extraction_id,toc_status)
            VALUES (:id,'Book','book.pdf',NULL,NULL,NULL,1,'2026-09-22T00:00:00Z',:sha,10,
                    'processed',NULL,NULL,NULL,'2026-09-22T00:00:01Z',:generation,'missing')"""),
            {'id': book_id, 'sha': 'a' * 64, 'generation': str(uuid4())})
        connection.execute(text("INSERT INTO pages VALUES (:id,1,10,:sha)"),
                           {'id': book_id, 'sha': 'b' * 64})
        connection.execute(text("INSERT INTO chapters VALUES (:chapter,:book,0,'Full document',1,1,1,'fallback')"),
                           {'chapter': chapter_id, 'book': book_id})
    engine.dispose()
    command.upgrade(migration_config(), 'head')
    engine = create_database_engine(database_path())
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM books')) == 1
        assert connection.scalar(text('SELECT count(*) FROM pages')) == 1
        assert connection.scalar(text('SELECT count(*) FROM chapters')) == 1
        assert connection.scalar(text('SELECT count(*) FROM learning_goals')) == 0
    engine.dispose()

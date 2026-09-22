import copy
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.config import database_path
from app.db.connection import create_database_engine
from app.db.migrations import migration_config
from app.main import create_app
from app.services.book_comparisons import normalize, keys
from test_book_profiles import body as profile_body, pdf


def setup(client, count=3, profiles=True):
    ids = []
    for index in range(count):
        response = client.post('/books', files={'file': (
            f'comparison-{index}.pdf', pdf(f'Comparison {index} {uuid4()}\n' + 'Machine readable technical content\n' * 4), 'application/pdf')})
        assert response.status_code == 201, response.text
        book_id = response.json()['id']
        ids.append(book_id)
        if profiles:
            assert client.put(f'/books/{book_id}/profile', json=profile_body()).status_code == 200
    goal = client.post('/learning-goals', json={
        'title': 'Study algorithms', 'description': 'For implementation', 'book_ids': ids}).json()
    return goal, sorted(ids)


def url(goal):
    return f"/learning-goals/{goal['id']}/comparison"


def payload(envelope):
    return {'input_token': envelope['input_token'],
            'expected_revision': envelope['saved']['revision'] if envelope['saved'] else None,
            'books': [{'book_id': book['book_id'], 'role': 'core', 'rationale': ' Primary resource ',
                       'relevance': {'category': 'high', 'explanation': ' Relevant topics '},
                       'depth': None, 'practice': None, 'focus_topics': [], 'evidence_refs': [],
                       'reviewed': True} for book in envelope['current']['books']]}


def save(client, goal):
    response = client.put(url(goal), json=payload(client.get(url(goal)).json()))
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('count', [3, 5])
def test_ready_deterministic_save_and_restart(library_client, count):
    goal, ids = setup(library_client, count)
    initial = library_client.get(url(goal)).json()
    assert initial == library_client.get(url(goal)).json()
    assert initial['readiness'] == {'ready': True, 'issues': []}
    assert [b['book_id'] for b in initial['current']['books']] == ids
    assert len(initial['current']['pairs']) == count * (count - 1) // 2
    assert initial['current']['coverage'][0]['book_ids'] == ids
    result = save(library_client, goal)
    assert not result['stale'] and result['saved']['revision'] == 1
    judgment = result['saved']['books'][0]
    assert judgment['rationale'] == 'Primary resource'
    assert judgment['relevance']['explanation'] == 'Relevant topics'
    assert judgment['provenance']['role'] == 'manual'
    assert judgment['provenance']['depth'] is None
    second = save(library_client, goal)
    assert second['saved']['revision'] == 2
    assert second['saved']['created_at'] == result['saved']['created_at']


def test_restart_persistence(migrated):
    with TestClient(create_app()) as client:
        goal, _ = setup(client)
        result = save(client, goal)
    with TestClient(create_app()) as client:
        assert client.get(url(goal)).json() == result


def test_save_and_delete_rollback(library_client, monkeypatch):
    from sqlalchemy.orm import Session
    def fail(*args):
        raise OSError('Simulated storage failure')
    goal, ids = setup(library_client)
    original = save(library_client, goal)
    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', fail)
        assert library_client.put(url(goal), json=payload(original)).status_code == 503
    assert library_client.get(url(goal)).json() == original
    setup(library_client)
    before = library_client.get(url(goal)).json()
    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', fail)
        assert library_client.delete(f'/books/{ids[0]}').status_code == 503
    assert library_client.get(url(goal)).json() == before
    assert library_client.get(f'/books/{ids[0]}').json()['file_available']


def test_matching_is_exact_unicode_and_preserves_profiles(library_client):
    assert normalize('  Straße\u2003\tTrees  ') == 'strasse trees'
    assert keys(['ML', 'ml', 'machine learning', 'C++', 'C']) == ['c', 'c++', 'machine learning', 'ml']
    goal, ids = setup(library_client)
    left = profile_body(main_topics=['Data  Structures', 'DATA\tSTRUCTURES', 'ML'],
                        prerequisites=[' Linear  Algebra '], difficulty='beginner')
    right = profile_body(main_topics=['data structures', 'machine learning'],
                         prerequisites=['linear algebra', 'Python'], difficulty='advanced')
    for book_id, body in zip(ids, [left, right, profile_body(prerequisites=[], difficulty=None)]):
        assert library_client.put(f'/books/{book_id}/profile', json=body).status_code == 200
    before = [library_client.get(f'/books/{i}/profile').json() for i in ids]
    result = library_client.get(url(goal)).json()['current']
    pair = result['pairs'][0]
    assert pair['overlap'] == {'shared': ['data structures'], 'left_only': ['ml'], 'right_only': ['machine learning']}
    assert pair['difficulty'] == 'lower'
    assert pair['prerequisites'] == {'shared': ['linear algebra'], 'left_only': [], 'right_only': ['python']}
    assert result['pairs'][1]['prerequisites'] is None
    assert result['pairs'][1]['difficulty'] == 'unknown'
    assert result['books'][0]['topic_count'] == 2
    assert [library_client.get(f'/books/{i}/profile').json() for i in ids] == before


def test_readiness_unknowns_and_no_processing_dependency(library_client):
    goal, ids = setup(library_client, profiles=False)
    result = library_client.get(url(goal)).json()
    assert result['current'] is None and result['input_token'] is None
    assert [i['code'] for i in result['readiness']['issues']] == ['profile_missing'] * 3
    for book_id in ids:
        library_client.put(f'/books/{book_id}/profile', json=profile_body(main_topics=[]))
    assert {i['code'] for i in library_client.get(url(goal)).json()['readiness']['issues']} == {'topics_missing'}
    request = {'input_token': 'a' * 64, 'expected_revision': None, 'books': [
        {'book_id': i, 'role': 'reference', 'rationale': 'R', 'relevance': {'category': 'unknown', 'explanation': 'Unsure'},
         'depth': None, 'practice': None, 'focus_topics': [], 'evidence_refs': [], 'reviewed': True} for i in ids]}
    assert library_client.put(url(goal), json=request).json()['error']['code'] == 'comparison_not_ready'
    for book_id in ids:
        library_client.put(f'/books/{book_id}/profile', json=profile_body(main_topics=['Topic'],
            difficulty=None, prerequisites=[], orientation=None, strengths=[], weaknesses=[], domain=None, suggested_use=None))
    assert library_client.get(url(goal)).json()['readiness']['ready']
    with library_client.app.state.database_engine.begin() as connection:
        connection.execute(text("UPDATE books SET processing_status='failed'"))
    assert save(library_client, goal)['saved']


@pytest.mark.parametrize('change', [
    {'role': 'automatic'}, {'rationale': ' '}, {'rationale': 'x' * 2001},
    {'reviewed': False}, {'reviewed': 'true'}, {'book_id': 'bad'},
    {'relevance': {'category': 'high', 'explanation': ''}},
    {'relevance': {'category': 'great', 'explanation': 'Because'}},
    {'depth': {'category': 'deep_treatment', 'explanation': ' '}},
    {'practice': {'category': 'substantial', 'explanation': 'x' * 1001}},
    {'focus_topics': ['unknown']}, {'focus_topics': ['algorithms', 'algorithms']},
    {'role': 'selected_chapters', 'focus_topics': []},
    {'evidence_refs': [{'kind': 'topic', 'topic': 'unknown'}]},
    {'evidence_refs': [{'kind': 'topic', 'topic': 'algorithms'}] * 2},
    {'evidence_refs': [{'kind': 'pair', 'other_book_id': str(uuid4()), 'dimension': 'overlap'}]},
    {'provenance': {'role': 'derived'}}, {'computed_results': {}},
])
def test_invalid_judgment_is_atomic(library_client, change):
    goal, _ = setup(library_client)
    prior = save(library_client, goal)
    request = payload(prior)
    request['books'][0].update(change)
    assert library_client.put(url(goal), json=request).status_code == 422
    assert library_client.get(url(goal)).json() == prior


def test_exact_membership_explicit_fields_and_unforgeable_inputs(library_client):
    goal, _ = setup(library_client)
    initial = library_client.get(url(goal)).json()
    request = payload(initial)
    for field in ('input_token', 'expected_revision', 'books'):
        invalid = copy.deepcopy(request)
        del invalid[field]
        assert library_client.put(url(goal), json=invalid).status_code == 422
    for field in request['books'][0]:
        invalid = copy.deepcopy(request)
        del invalid['books'][0][field]
        assert library_client.put(url(goal), json=invalid).status_code == 422
    for ids in [request['books'][:2], request['books'] * 2,
                [request['books'][0]] * 3,
                [{**request['books'][0], 'book_id': str(uuid4())}, *request['books'][1:]]]:
        assert library_client.put(url(goal), json={**request, 'books': ids}).status_code == 422
    for field in ('provenance', 'snapshot', 'current'):
        assert library_client.put(url(goal), json={**request, field: {}}).status_code == 422
    assert library_client.get(url(goal)).json()['saved'] is None


def test_roles_assessments_and_evidence(library_client):
    goal, ids = setup(library_client, 5)
    request = payload(library_client.get(url(goal)).json())
    for index, item in enumerate(request['books']):
        item['role'] = ['core', 'selected_chapters', 'reference', 'skip_for_now', 'core'][index]
        item['focus_topics'] = ['algorithms']
        item['depth'] = {'category': 'working_detail', 'explanation': 'Practical study'}
        item['practice'] = {'category': 'some', 'explanation': 'My assessment, not inferred'}
        item['relevance'] = {'category': 'unknown', 'explanation': 'Not yet studied'}
        item['evidence_refs'] = [{'kind': 'profile_field', 'field': 'main_topics'},
            {'kind': 'topic', 'topic': 'algorithms'},
            {'kind': 'pair', 'other_book_id': ids[(index + 1) % 5], 'dimension': 'overlap'}]
    result = library_client.put(url(goal), json=request)
    assert result.status_code == 200, result.text
    assert set(result.json()['saved']['books'][0]['provenance'].values()) == {'manual'}


def test_stale_inputs_concurrency_and_inactive_history(library_client):
    goal, ids = setup(library_client)
    request = payload(library_client.get(url(goal)).json())
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: library_client.put(url(goal), json=request), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    original = library_client.get(url(goal)).json()
    library_client.put(f'/books/{ids[0]}/profile', json=profile_body(main_topics=['New topic']))
    stale = library_client.get(url(goal)).json()
    assert stale['stale'] and stale['saved'] == original['saved']
    old = payload(original)
    assert library_client.put(url(goal), json=old).json()['error']['code'] == 'comparison_inputs_changed'
    refreshed = save(library_client, goal)
    assert not refreshed['stale'] and refreshed['saved']['revision'] == 2
    new_goal = library_client.post('/learning-goals', json={'title': 'New', 'description': None, 'book_ids': ids}).json()
    inactive = library_client.get(url(goal)).json()
    assert inactive['saved'] == refreshed['saved'] and inactive['current'] is None
    assert library_client.put(url(goal), json=payload(refreshed)).json()['error']['code'] == 'goal_inactive'
    assert library_client.get(url(new_goal)).json()['saved'] is None
    assert library_client.get(f'/learning-goals/{uuid4()}/comparison').status_code == 404
    assert library_client.get('/learning-goals/bad/comparison').status_code == 422


def test_deletion_cleanup_and_unrelated_snapshot(library_client):
    old, old_ids = setup(library_client)
    saved = save(library_client, old)
    assert library_client.delete(f'/books/{old_ids[0]}').status_code == 409
    assert library_client.get(url(old)).json() == saved
    current, _ = setup(library_client)
    unrelated = save(library_client, current)
    assert library_client.delete(f'/books/{old_ids[0]}').status_code == 204
    assert library_client.get(url(old)).json()['saved'] is None
    assert library_client.get(url(current)).json() == unrelated
    with library_client.app.state.database_engine.connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM book_comparisons')) == 1
        assert connection.scalar(text('SELECT count(*) FROM book_comparison_books')) == 3
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []


def test_corrupt_snapshot_safe_error(library_client):
    goal, _ = setup(library_client)
    save(library_client, goal)
    with library_client.app.state.database_engine.begin() as connection:
        connection.execute(text("UPDATE book_comparisons SET snapshot_json='{}'"))
    response = library_client.get(url(goal))
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'library_storage_unavailable'


def test_selection_review_invalidated_references_and_processing_independence(library_client):
    goal, ids = setup(library_client, 5)
    initial = save(library_client, goal)
    assert library_client.post(f'/books/{ids[0]}/process').status_code == 200
    assert library_client.get(url(goal)).json() == initial
    assert library_client.put(f"/learning-goals/{goal['id']}/books", json={'book_ids': ids[1:]}).status_code == 200
    stale = library_client.get(url(goal)).json()
    assert stale['stale'] and stale['saved'] == initial['saved']
    assert stale['current']['goal']['book_ids'] == ids[1:]
    updated = save(library_client, goal)
    # Removing a book from a replacement snapshot also removes its membership.
    assert library_client.delete(f'/books/{ids[0]}').status_code == 204
    assert library_client.get(url(goal)).json() == updated
    library_client.put(f'/books/{ids[1]}/profile', json=profile_body(main_topics=['New topic']))
    current = library_client.get(url(goal)).json()
    request = payload(current)
    request['books'][0]['evidence_refs'] = [{'kind': 'topic', 'topic': 'algorithms'}]
    assert library_client.put(url(goal), json=request).status_code == 422
    library_client.put(f'/books/{ids[1]}/profile', json=profile_body(main_topics=[]))
    unready = library_client.get(url(goal)).json()
    assert unready['current'] is None and unready['saved'] == updated['saved'] and unready['stale']


def test_invalid_selection_and_missing_rows_are_explicit_readiness_issues(library_client):
    goal, ids = setup(library_client)
    with library_client.app.state.database_engine.begin() as connection:
        connection.execute(text('DELETE FROM learning_goal_books WHERE goal_id=:goal AND book_id=:book'),
                           {'goal': goal['id'], 'book': ids[0]})
    result = library_client.get(url(goal)).json()
    assert result['current'] is None
    assert result['readiness']['issues'][0]['code'] == 'invalid_book_selection'


def test_empty_field_and_unknown_pair_are_not_evidence(library_client):
    goal, ids = setup(library_client)
    library_client.put(f'/books/{ids[0]}/profile', json=profile_body(prerequisites=[], difficulty=None))
    initial = library_client.get(url(goal)).json()
    for ref in [{'kind': 'profile_field', 'field': 'prerequisites'},
                {'kind': 'pair', 'other_book_id': ids[1], 'dimension': 'difficulty'},
                {'kind': 'pair', 'other_book_id': ids[1], 'dimension': 'prerequisites'},
                {'kind': 'pair', 'other_book_id': ids[0], 'dimension': 'overlap'}]:
        request = payload(initial)
        request['books'][0]['evidence_refs'] = [ref]
        assert library_client.put(url(goal), json=request).status_code == 422
    request = payload(initial)
    for item in request['books']:
        item['role'] = 'skip_for_now'
    assert library_client.put(url(goal), json=request).status_code == 200


def test_populated_m4_migration_and_disposable_downgrade(monkeypatch):
    import app.db.migrations as migrations
    command.upgrade(migration_config(), '0004_book_profiles')
    monkeypatch.setattr(migrations, 'REVISION', '0004_book_profiles')
    with TestClient(create_app()) as client:
        goal, ids = setup(client)
        assert client.post(f'/books/{ids[0]}/process').status_code == 200
    engine = create_database_engine(database_path())
    tables = [t for t in inspect(engine).get_table_names() if t != 'alembic_version']
    with engine.connect() as connection:
        before = {table: connection.execute(text(f'SELECT * FROM {table}')).all() for table in tables}
    artifacts = {p: p.read_bytes() for p in database_path().parent.rglob('*')
                 if p.is_file() and p.suffix in ('.pdf', '.json', '.txt')}
    command.upgrade(migration_config(), 'head')
    command.upgrade(migration_config(), 'head')
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0005_book_comparisons'
        assert {table: connection.execute(text(f'SELECT * FROM {table}')).all() for table in tables} == before
    assert all(p.read_bytes() == value for p, value in artifacts.items())
    assert set(inspect(engine).get_table_names()) == set(tables) | {'alembic_version', 'book_comparisons', 'book_comparison_books'}
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("INSERT INTO book_comparisons VALUES (:id,0,:token,'v','{}','now','now')"),
                           {'id': goal['id'], 'token': 'a' * 64})
    command.downgrade(migration_config(), '0004_book_profiles')
    with engine.connect() as connection:
        assert {table: connection.execute(text(f'SELECT * FROM {table}')).all() for table in tables} == before
    engine.dispose()


def test_database_constraints_and_comparison_cascade(library_client):
    goal, ids = setup(library_client)
    save(library_client, goal)
    engine = library_client.app.state.database_engine
    for statement, parameters in [
        ('UPDATE book_comparisons SET revision=0', {}),
        ("UPDATE book_comparisons SET input_fingerprint='invalid'", {}),
        ('INSERT INTO book_comparison_books (goal_id,book_id) VALUES (:goal,:book)',
         {'goal': goal['id'], 'book': ids[0]}),
        ('INSERT INTO book_comparison_books (goal_id,book_id) VALUES (:goal,:book)',
         {'goal': goal['id'], 'book': str(uuid4())}),
    ]:
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(text(statement), parameters)
    with engine.begin() as connection:
        connection.execute(text('DELETE FROM book_comparisons WHERE goal_id=:goal'), {'goal': goal['id']})
        assert connection.scalar(text('SELECT count(*) FROM book_comparison_books')) == 0
        assert connection.scalar(text('SELECT count(*) FROM books')) == 3

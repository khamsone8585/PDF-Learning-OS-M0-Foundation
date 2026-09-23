import json
import time
from uuid import uuid4

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import database_path
from app.db.connection import create_database_engine
from app.db.migrations import migration_config
from app.main import create_app
from app.models.book import Book
from app.models.book_profile import BookProfile
from test_book_profiles import body as profile_body, pdf


def add_book(client, index, *, title=None, author='Author', edition=None, year=None, profile=None):
    fields = {'title': title or f'Book {index}', 'author': author}
    if edition is not None:
        fields['edition'] = edition
    if year is not None:
        fields['year'] = str(year)
    response = client.post('/books', data=fields, files={'file': (
        f'book-{index}.pdf', pdf(f'Unique {index} {uuid4()}\n' + 'Technical content\n' * 5),
        'application/pdf')})
    assert response.status_code == 201, response.text
    item = response.json()
    if profile is not None:
        saved = client.put(f"/books/{item['id']}/profile", json=profile)
        assert saved.status_code == 200, saved.text
    return item


def triage_body(scope='library_snapshot', ids=None):
    return {'title': 'Learn systems', 'description': 'Build practical foundations',
            'target_topics': ['Distributed Systems', 'Algorithms'], 'target_domain': 'Computer Science',
            'difficulty_ceiling': 'intermediate',
            'scope': {'kind': scope, 'book_ids': ids or []}}


def judgments(envelope, ids):
    books = []
    for index, book_id in enumerate(ids):
        candidate = next(item for item in envelope['candidates'] if item['book_id'] == book_id)
        books.append({'book_id': book_id, 'role': 'core' if index == 0 else 'selected_chapters',
                      'rationale': 'Explicit learner decision',
                      'relevance': {'category': 'high', 'explanation': 'Exact target evidence'},
                      'depth': None, 'practice': None,
                      'focus_topics': [] if index == 0 else [candidate['topic_keys'][0]],
                      'evidence_refs': [], 'reviewed': True})
    return {'input_token': envelope['input_token'],
            'expected_revision': envelope['session']['revision'],
            'reviewed_recommendation': True, 'books': books}


def ready_library(client, count=5):
    topics = [
        ['Distributed Systems', 'Consensus'], ['Algorithms', 'Data Structures'],
        ['Consensus', 'Networking'], ['Computer Architecture'], ['Operating Systems'],
    ]
    result = []
    for index in range(count):
        result.append(add_book(client, index, profile=profile_body(
            domain='Computer Science', main_topics=topics[index % len(topics)],
            prerequisites=['Algorithms'] if index == 0 else [],
            difficulty='intermediate', orientation='balanced')))
    return result


def seed_synthetic_library(client, count):
    timestamp = '2026-09-23T00:00:00Z'
    with Session(client.app.state.library.engine) as session:
        for index in range(count):
            book_id = str(uuid4())
            topics = [f'Topic {index % 12}', f'Shared {index % 4}']
            session.add(Book(
                id=book_id, title=f'Synthetic {index:03d}', original_filename=f'{index}.pdf',
                author=f'Author {index}', edition=None, year=2020 + index % 5, page_count=1,
                imported_at=timestamp, sha256=f'{index + 1:064x}', size_bytes=1,
                processing_status='unprocessed', processing_error_code=None,
                processing_error_message=None, processing_started_at=None, processed_at=None,
                active_extraction_id=None, toc_status=None,
            ))
            session.add(BookProfile(
                book_id=book_id, domain='Systems', difficulty='intermediate',
                prerequisites_json='[]', main_topics_json=json.dumps(topics),
                orientation='balanced', strengths_json='[]', weaknesses_json='[]',
                suggested_use=None, domain_source='manual', difficulty_source='manual',
                prerequisites_source=None, main_topics_source='manual', orientation_source='manual',
                strengths_source=None, weaknesses_source=None, suggested_use_source=None,
                created_at=timestamp, updated_at=timestamp,
            ))
        session.commit()


@pytest.mark.parametrize('count', [30, 100])
def test_large_library_map_is_stable_paginated_and_batched(library_client, count, record_property):
    seed_synthetic_library(library_client, count)
    engine = library_client.app.state.library.engine
    statements = []

    def count_selects(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement)

    event.listen(engine, 'before_cursor_execute', count_selects)
    started = time.perf_counter()
    try:
        first = library_client.get('/library-intelligence/map')
    finally:
        elapsed = time.perf_counter() - started
        event.remove(engine, 'before_cursor_execute', count_selects)
    assert first.status_code == 200, first.text
    assert first.json()['counts']['books'] == count
    assert len(first.json()['books']) == count
    assert len(statements) <= 3
    second = library_client.get('/library-intelligence/map')
    assert [book['book_id'] for book in second.json()['books']] == [
        book['book_id'] for book in first.json()['books']]
    page = library_client.get('/library-intelligence/relations?kind=topic_overlap&limit=25').json()
    assert len(page['items']) == 25
    assert page['total'] <= count * (count - 1) // 2
    if count == 100:
        record_property('library_map_100_books_seconds', round(elapsed, 6))


def test_map_overlap_and_prerequisites_are_exact(library_client):
    books = ready_library(library_client)
    missing = add_book(library_client, 9, title='Unprofiled', author=None)
    mapped = library_client.get('/library-intelligence/map')
    assert mapped.status_code == 200, mapped.text
    data = mapped.json()
    assert data['exact_content_duplicates_prevented'] is True
    assert data['counts']['books'] == 6
    assert data['counts']['profile_missing'] == 1
    assert len(data['library_token']) == 64
    assert 'sha256' not in mapped.text
    overlaps = library_client.get('/library-intelligence/relations?kind=topic_overlap&limit=100').json()
    assert overlaps['total'] >= 1
    assert any(item['shared_topics'] == ['consensus'] for item in overlaps['items'])
    prerequisites = library_client.get('/library-intelligence/prerequisites?limit=100').json()['items']
    target = next(item for item in prerequisites if item['book_id'] == books[0]['id'])
    assert target['normalized_key'] == 'algorithms'
    assert {provider['book_id'] for provider in target['providers']} == {books[1]['id']}
    assert not target['unresolved']
    assert library_client.get(f"/library-intelligence/prerequisites?book_id={missing['id']}").json()['total'] == 0


def test_bibliographic_candidates_and_persisted_reviews(library_client):
    first = add_book(library_client, 1, title='  Systems   Design ', author='A. Author', edition='2', year=2020)
    second = add_book(library_client, 2, title='systems design', author='a. author', edition='3', year=2022)
    add_book(library_client, 3, title='Systems Design!', author='A. Author')
    page = library_client.get('/library-intelligence/relations?kind=bibliographic').json()
    assert page['total'] == 1
    assert page['items'][0]['classification'] == 'related_edition'
    pair = sorted((first['id'], second['id']))
    review = library_client.put('/library-intelligence/relation-reviews', json={
        'left_book_id': pair[1], 'right_book_id': pair[0], 'decision': 'related_edition',
        'preferred_book_id': None, 'note': 'Keep both editions'})
    assert review.status_code == 200, review.text
    assert review.json()['left_book_id'] == pair[0]
    assert library_client.get('/library-intelligence/relations?kind=bibliographic').json()['items'][0]['review']['source'] == 'manual'
    invalid = library_client.put('/library-intelligence/relation-reviews', json={
        'left_book_id': pair[0], 'right_book_id': pair[1], 'decision': 'same_work',
        'preferred_book_id': str(uuid4()), 'note': None})
    assert invalid.status_code == 422


def test_triage_shortlist_staleness_update_and_restart(library_client):
    books = ready_library(library_client)
    created = library_client.post('/curriculum-triages', json=triage_body())
    assert created.status_code == 201, created.text
    envelope = created.json()
    assert not envelope['stale']
    assert 3 <= len(envelope['recommendation']['suggested_book_ids']) <= 5
    assert envelope == library_client.get(f"/curriculum-triages/{envelope['session']['id']}").json()
    library_client.put(f"/books/{books[0]['id']}/profile", json=profile_body(
        domain='Computer Science', main_topics=['Distributed Systems', 'Consensus', 'Replication'],
        prerequisites=['Algorithms'], difficulty='intermediate', orientation='balanced'))
    stale = library_client.get(f"/curriculum-triages/{envelope['session']['id']}").json()
    assert stale['stale'] and 'inputs_changed' in stale['stale_reasons']
    updated_body = {**triage_body(), 'input_token': stale['input_token'],
                    'expected_revision': stale['session']['revision']}
    updated = library_client.put(f"/curriculum-triages/{envelope['session']['id']}", json=updated_body)
    assert updated.status_code == 200, updated.text
    assert not updated.json()['stale'] and updated.json()['session']['revision'] == 2


def test_shortlist_avoids_unreviewed_probable_duplicates_and_honors_preference(library_client):
    duplicate_profile = profile_body(
        domain='Computer Science', main_topics=['Distributed Systems', 'Consensus'],
        prerequisites=[], difficulty='intermediate', orientation='balanced')
    first = add_book(library_client, 30, title='Systems Handbook', author='Exact Author',
                     profile=duplicate_profile)
    second = add_book(library_client, 31, title='  systems   handbook ', author='exact author',
                      profile=duplicate_profile)
    ready_library(library_client, 3)
    envelope = library_client.post('/curriculum-triages', json=triage_body()).json()
    suggested = set(envelope['recommendation']['suggested_book_ids'])
    assert not {first['id'], second['id']} <= suggested
    pair = sorted((first['id'], second['id']))
    reviewed = library_client.put('/library-intelligence/relation-reviews', json={
        'left_book_id': pair[0], 'right_book_id': pair[1], 'decision': 'same_work',
        'preferred_book_id': second['id'], 'note': 'Retain the clearer scan'})
    assert reviewed.status_code == 200, reviewed.text
    refreshed = library_client.get(f"/curriculum-triages/{envelope['session']['id']}").json()
    assert refreshed['stale']
    assert first['id'] not in refreshed['recommendation']['suggested_book_ids']


def test_shortlist_returns_partial_instead_of_padding_without_evidence(library_client):
    add_book(library_client, 40, profile=profile_body(main_topics=['Distributed Systems']))
    add_book(library_client, 41, profile=profile_body(main_topics=['Unrelated']))
    add_book(library_client, 42)
    response = library_client.post('/curriculum-triages', json=triage_body())
    assert response.status_code == 201, response.text
    recommendation = response.json()['recommendation']
    assert recommendation['partial']
    assert len(recommendation['suggested_book_ids']) < 3
    assert 'insufficient_recommendation_evidence' in {
        issue['code'] for issue in recommendation['issues']}


def test_whole_library_sync_and_selected_scope(library_client):
    books = ready_library(library_client, 3)
    whole = library_client.post('/curriculum-triages', json=triage_body()).json()
    added = add_book(library_client, 8, profile=profile_body(main_topics=['Algorithms']))
    stale = library_client.get(f"/curriculum-triages/{whole['session']['id']}").json()
    assert 'library_membership_changed' in stale['stale_reasons']
    synced = library_client.put(f"/curriculum-triages/{whole['session']['id']}", json={
        **triage_body(), 'input_token': stale['input_token'],
        'expected_revision': stale['session']['revision']}).json()
    assert added['id'] in synced['session']['book_ids'] and not synced['stale']
    selected = library_client.post('/curriculum-triages', json={
        **triage_body('selected', [book['id'] for book in books]),
        'archive_draft_id': synced['session']['id']})
    assert selected.status_code == 201, selected.text
    add_book(library_client, 10, profile=profile_body(main_topics=['New Topic']))
    assert not library_client.get(f"/curriculum-triages/{selected.json()['session']['id']}").json()['stale']


def test_atomic_confirmation_creates_goal_and_comparison(library_client):
    ready_library(library_client)
    envelope = library_client.post('/curriculum-triages', json=triage_body()).json()
    chosen = envelope['recommendation']['suggested_book_ids'][:3]
    response = library_client.post(f"/curriculum-triages/{envelope['session']['id']}/confirm",
                                   json=judgments(envelope, chosen))
    assert response.status_code == 201, response.text
    result = response.json()
    assert result['triage']['status'] == 'applied'
    assert result['goal']['book_ids'] == sorted(chosen) and result['goal']['is_active']
    assert result['comparison']['saved']['revision'] == 1 and not result['comparison']['stale']
    assert library_client.get('/learning-goals/active').json()['goal']['id'] == result['goal']['id']
    assert library_client.get(f"/learning-goals/{result['goal']['id']}/comparison").json() == result['comparison']
    assert library_client.post(f"/curriculum-triages/{envelope['session']['id']}/confirm",
                               json=judgments(envelope, chosen)).status_code == 409


@pytest.mark.parametrize('roles,code', [
    (['reference', 'reference', 'reference'], 'primary_book_required'),
    (['core', 'reference', 'skip_for_now'], 'later_not_study_now'),
])
def test_confirmation_role_boundaries_are_atomic(library_client, roles, code):
    ready_library(library_client)
    envelope = library_client.post('/curriculum-triages', json=triage_body()).json()
    chosen = envelope['recommendation']['suggested_book_ids'][:3]
    request = judgments(envelope, chosen)
    for item, role in zip(request['books'], roles):
        item['role'] = role
        if role != 'selected_chapters':
            item['focus_topics'] = []
    response = library_client.post(f"/curriculum-triages/{envelope['session']['id']}/confirm", json=request)
    assert response.status_code == 422 and response.json()['error']['code'] == code
    assert library_client.get('/learning-goals/active').json()['goal'] is None
    assert library_client.get(f"/curriculum-triages/{envelope['session']['id']}").json()['session']['status'] == 'draft'


def test_deletion_stales_draft_and_invalidates_applied_history(library_client):
    books = ready_library(library_client)
    draft = library_client.post('/curriculum-triages', json=triage_body('selected', [b['id'] for b in books])).json()
    assert library_client.delete(f"/books/{books[4]['id']}").status_code == 204
    assert 'candidate_deleted' in library_client.get(f"/curriculum-triages/{draft['session']['id']}").json()['stale_reasons']
    synced = library_client.get(f"/curriculum-triages/{draft['session']['id']}").json()
    update = {**triage_body('selected', synced['session']['book_ids']), 'input_token': synced['input_token'],
              'expected_revision': synced['session']['revision']}
    current = library_client.put(f"/curriculum-triages/{draft['session']['id']}", json=update).json()
    chosen = current['recommendation']['suggested_book_ids'][:3]
    applied = library_client.post(f"/curriculum-triages/{draft['session']['id']}/confirm",
                                  json=judgments(current, chosen)).json()
    other = [add_book(library_client, 20 + i, profile=profile_body(main_topics=['Other']))['id'] for i in range(3)]
    library_client.post('/learning-goals', json={'title': 'Other', 'description': None, 'book_ids': other})
    assert library_client.delete(f'/books/{chosen[0]}').status_code == 204
    history = library_client.get(f"/curriculum-triages/{applied['triage']['id']}").json()
    assert history['session']['status'] == 'invalidated'


def test_populated_m5_upgrade_preserves_data_and_constraints(monkeypatch):
    import app.db.migrations as migrations
    command.upgrade(migration_config(), '0005_book_comparisons')
    monkeypatch.setattr(migrations, 'REVISION', '0005_book_comparisons')
    with TestClient(create_app()) as client:
        ready_library(client, 3)
    engine = create_database_engine(database_path())
    old_tables = [name for name in inspect(engine).get_table_names() if name != 'alembic_version']
    with engine.connect() as connection:
        before = {name: connection.execute(text(f'SELECT * FROM {name}')).all() for name in old_tables}
    command.upgrade(migration_config(), 'head')
    command.upgrade(migration_config(), 'head')
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0006_library_intelligence'
        assert {name: connection.execute(text(f'SELECT * FROM {name}')).all() for name in old_tables} == before
    assert set(inspect(engine).get_table_names()) == set(old_tables) | {
        'alembic_version', 'curriculum_triages', 'curriculum_triage_books', 'library_relation_reviews'}
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("INSERT INTO curriculum_triages VALUES "
            "('x','T',NULL,NULL,'[]',NULL,'selected',0,:fp,:fp,'v','draft',NULL,'n','n',NULL)"),
            {'fp': 'a' * 64})
    command.downgrade(migration_config(), '0005_book_comparisons')
    with engine.connect() as connection:
        assert {name: connection.execute(text(f'SELECT * FROM {name}')).all() for name in old_tables} == before
    engine.dispose()

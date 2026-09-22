import hashlib
from uuid import uuid4

import pymupdf
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.config import database_path
from app.db.connection import create_database_engine
from app.db.migrations import migration_config
from app.main import create_app
from app.models.book import Book, Chapter, Page
from app.services.library_errors import LibraryError
from app.services.pdf_processing import machine_readable, normalize_toc
from test_library import root, upload


def text_pdf(pages, toc=None):
    with pymupdf.open() as document:
        for value in pages:
            page = document.new_page()
            if value:
                page.insert_text((72, 72), value)
        if toc is not None:
            document.set_toc(toc)
        return document.tobytes()


def imported(client, pages=None, toc=None):
    data = text_pdf(pages or ['Machine readable technical content ' * 4], toc)
    response = upload(client, data)
    assert response.status_code == 201
    return response.json(), data


def test_exact_multi_page_extraction_and_fallback(library_client):
    book, data = imported(library_client, ['First page technical content ' * 4,
                                           'Second page machine readable content ' * 4])
    response = library_client.post(f"/books/{book['id']}/process")
    assert response.status_code == 200
    processed = response.json()
    assert processed['processing_status'] == 'processed'
    assert processed['has_processed_content'] and processed['toc_status'] == 'missing'
    generation = next((root() / 'books' / book['id'] / 'extracted').iterdir())
    with pymupdf.open(stream=data, filetype='pdf') as document:
        expected = [page.get_text('text', sort=False) for page in document]
    for number, value in enumerate(expected, 1):
        assert (generation / 'pages' / f'{number:06d}.txt').read_bytes() == value.encode('utf-8')
    with Session(library_client.app.state.database_engine) as session:
        pages = list(session.scalars(select(Page).where(Page.book_id == book['id']).order_by(Page.page_number)))
        assert [page.page_number for page in pages] == [1, 2]
        assert [page.char_count for page in pages] == list(map(len, expected))
        assert pages[0].text_sha256 == hashlib.sha256(expected[0].encode()).hexdigest()
    outline = library_client.get(f"/books/{book['id']}/chapters").json()
    assert outline['structure_source'] == 'fallback'
    assert outline['chapters'][0] | {'id': None} == {
        'id': None, 'title': 'Full document', 'position': 0, 'level': 1,
        'start_page': 1, 'end_page': 2, 'source': 'fallback'}


def test_nested_toc_mapping(library_client):
    toc = [[1, 'Chapter one', 1], [2, 'Section one', 2], [1, 'Chapter two', 4]]
    book, _data = imported(library_client, ['Readable content ' * 5] * 4, toc)
    assert library_client.post(f"/books/{book['id']}/process").status_code == 200
    outline = library_client.get(f"/books/{book['id']}/chapters").json()
    assert outline['toc_status'] == 'available' and outline['structure_source'] == 'toc'
    assert [(c['title'], c['level'], c['start_page'], c['end_page']) for c in outline['chapters']] == [
        ('Chapter one', 1, 1, 3), ('Section one', 2, 2, 3), ('Chapter two', 1, 4, 4)]
    assert library_client.put(f"/books/{book['id']}/chapters",
                              json={'sections': [{'title': 'No', 'start_page': 1}]}).status_code == 409


def test_toc_normalization_is_deterministic():
    chapters, status = normalize_toc([
        [3, ' Root ', 1], [7, 'Child', 2], ['bad', 'Skip', 3], [1, 'Back', 1],
        [1, '', 4], [1, 'Next', 5],
    ], 6)
    assert status == 'partial'
    assert [(c.title, c.level, c.start_page, c.end_page) for c in chapters] == [
        ('Root', 1, 1, 4), ('Child', 2, 2, 4), ('Next', 1, 5, 6)]
    fallback, status = normalize_toc([[1, '', 99]], 3)
    assert status == 'invalid' and fallback[0].source == 'fallback'


def test_machine_readable_boundaries():
    assert not machine_readable(['a' * 49])
    assert not machine_readable(['a' * 19, 'b' * 19, 'c' * 12])
    assert machine_readable(['a' * 20, 'b' * 30])


def test_ocr_required_has_no_partial_generation(library_client):
    book, _data = imported(library_client, [''])
    response = library_client.post(f"/books/{book['id']}/process")
    assert response.status_code == 422 and response.json()['error']['code'] == 'ocr_required'
    details = library_client.get(f"/books/{book['id']}").json()
    assert details['processing_status'] == 'failed' and not details['has_processed_content']
    assert details['processing_error']['code'] == 'ocr_required'
    assert list((root() / '.processing').iterdir()) == []
    assert not (root() / 'books' / book['id'] / 'extracted').exists()


def test_manual_correction_and_reprocess_preserve_structure(library_client):
    book, _data = imported(library_client, ['Readable page content ' * 5] * 3)
    assert library_client.post(f"/books/{book['id']}/process").status_code == 200
    corrected = library_client.put(f"/books/{book['id']}/chapters", json={'sections': [
        {'title': 'Start', 'start_page': 1}, {'title': 'Finish', 'start_page': 3},
    ]})
    assert corrected.status_code == 200
    assert [(c['title'], c['start_page'], c['end_page'], c['source']) for c in corrected.json()['chapters']] == [
        ('Start', 1, 2, 'manual'), ('Finish', 3, 3, 'manual')]
    assert library_client.post(f"/books/{book['id']}/process").status_code == 200
    assert [c['title'] for c in library_client.get(f"/books/{book['id']}/chapters").json()['chapters']] == [
        'Start', 'Finish']


def test_failed_reprocess_preserves_previous_generation(library_client, monkeypatch):
    book, _data = imported(library_client)
    assert library_client.post(f"/books/{book['id']}/process").status_code == 200
    original_generation = next((root() / 'books' / book['id'] / 'extracted').iterdir()).name
    with monkeypatch.context() as patch:
        patch.setattr('app.services.processing.extract_pdf', lambda *_args: (_ for _ in ()).throw(
            LibraryError(422, 'extraction_failed', 'Text could not be extracted from this PDF.')))
        assert library_client.post(f"/books/{book['id']}/process").status_code == 422
    details = library_client.get(f"/books/{book['id']}").json()
    assert details['processing_status'] == 'failed' and details['has_processed_content']
    assert (root() / 'books' / book['id'] / 'extracted' / original_generation).exists()
    assert library_client.get(f"/books/{book['id']}/chapters").json()['chapters']


def test_changed_or_missing_source_fails_safely(library_client):
    book, _data = imported(library_client)
    original = root() / 'books' / book['id'] / 'original.pdf'
    original.write_bytes(text_pdf(['Different readable source content ' * 4]))
    response = library_client.post(f"/books/{book['id']}/process")
    assert response.status_code == 409 and response.json()['error']['code'] == 'source_file_changed'
    original.unlink()
    assert library_client.post(f"/books/{book['id']}/process").json()['error']['code'] == 'source_file_missing'


def test_processing_restart_and_delete_cleanup(migrated):
    with TestClient(create_app()) as client:
        book, _data = imported(client)
        assert client.post(f"/books/{book['id']}/process").status_code == 200
    with TestClient(create_app()) as client:
        assert client.get(f"/books/{book['id']}").json()['processing_status'] == 'processed'
        assert client.delete(f"/books/{book['id']}").status_code == 204
        with Session(client.app.state.database_engine) as session:
            assert session.scalars(select(Page).where(Page.book_id == book['id'])).all() == []
            assert session.scalars(select(Chapter).where(Chapter.book_id == book['id'])).all() == []
    assert not (root() / 'books' / book['id']).exists()


def test_interrupted_state_recovers_as_failed(migrated):
    with TestClient(create_app()) as client:
        book, _data = imported(client)
        with client.app.state.database_engine.begin() as connection:
            connection.execute(text("UPDATE books SET processing_status='processing' WHERE id=:id"), {'id': book['id']})
    with TestClient(create_app()) as client:
        details = client.get(f"/books/{book['id']}").json()
        assert details['processing_status'] == 'failed'
        assert details['processing_error']['code'] == 'processing_interrupted'


def test_processing_and_correction_conflicts(library_client):
    book, _data = imported(library_client)
    with library_client.app.state.database_engine.begin() as connection:
        connection.execute(text("UPDATE books SET processing_status='processing' WHERE id=:id"), {'id': book['id']})
    assert library_client.post(f"/books/{book['id']}/process").status_code == 409
    assert library_client.delete(f"/books/{book['id']}").status_code == 409
    assert library_client.put(f"/books/{book['id']}/chapters",
                              json={'sections': [{'title': 'One', 'start_page': 1}]}).status_code == 409


def test_invalid_manual_ranges_rollback(library_client):
    book, _data = imported(library_client, ['Readable content ' * 6] * 3)
    assert library_client.post(f"/books/{book['id']}/process").status_code == 200
    before = library_client.get(f"/books/{book['id']}/chapters").json()
    for sections in ([{'title': 'Late', 'start_page': 2}],
                     [{'title': 'One', 'start_page': 1}, {'title': 'Same', 'start_page': 1}],
                     [{'title': 'One', 'start_page': 1}, {'title': 'Past', 'start_page': 4}],
                     [{'title': '   ', 'start_page': 1}]):
        assert library_client.put(f"/books/{book['id']}/chapters", json={'sections': sections}).status_code == 422
        assert library_client.get(f"/books/{book['id']}/chapters").json()['chapters'] == before['chapters']


def test_processing_commit_acknowledgement_loss_is_success(library_client, monkeypatch):
    book, _data = imported(library_client)
    original_commit = Session.commit
    calls = 0

    def uncertain(session):
        nonlocal calls
        calls += 1
        original_commit(session)
        if calls == 2:
            raise OSError('lost acknowledgement')

    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', uncertain)
        response = library_client.post(f"/books/{book['id']}/process")
    assert response.status_code == 200
    assert response.json()['processing_status'] == 'processed'
    assert len(list((root() / 'books' / book['id'] / 'extracted').iterdir())) == 1


def test_processing_commit_failure_removes_new_generation(library_client, monkeypatch):
    book, _data = imported(library_client)
    original_commit = Session.commit
    calls = 0

    def fail_second(session):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('commit failed')
        original_commit(session)

    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', fail_second)
        response = library_client.post(f"/books/{book['id']}/process")
    assert response.status_code == 503
    details = library_client.get(f"/books/{book['id']}").json()
    assert details['processing_status'] == 'failed' and not details['has_processed_content']
    assert not (root() / 'books' / book['id'] / 'extracted').exists()


def test_old_generation_cleanup_pending_recovers(library_client, monkeypatch):
    book, _data = imported(library_client)
    assert library_client.post(f"/books/{book['id']}/process").status_code == 200
    service = library_client.app.state.library
    original_remove = service.storage.remove_generation
    with monkeypatch.context() as patch:
        patch.setattr(service.storage, 'remove_generation', lambda *_args: (_ for _ in ()).throw(OSError('disk')))
        response = library_client.post(f"/books/{book['id']}/process")
        assert response.status_code == 503
        assert response.json()['error']['code'] == 'processing_cleanup_pending'
        assert service.blocked
    assert library_client.post(f"/books/{book['id']}/process").status_code == 200
    assert not service.blocked
    assert len(list((root() / 'books' / book['id'] / 'extracted').iterdir())) == 1
    assert callable(original_remove)


def test_startup_reconciles_missing_and_unreferenced_generations(migrated):
    with TestClient(create_app()) as client:
        book, _data = imported(client)
        assert client.post(f"/books/{book['id']}/process").status_code == 200
        details = client.get(f"/books/{book['id']}").json()
        assert details['has_processed_content']
        extracted = root() / 'books' / book['id'] / 'extracted'
        active = next(extracted.iterdir())
        extra = extracted / str(uuid4())
        extra.mkdir(); (extra / 'pages').mkdir(); (extra / 'pages' / '000001.txt').write_text('orphan')
        for page in (active / 'pages').iterdir():
            page.unlink()
        (active / 'pages').rmdir(); active.rmdir()
    with TestClient(create_app()) as client:
        details = client.get(f"/books/{book['id']}").json()
        assert details['processing_status'] == 'failed' and not details['has_processed_content']
        assert details['processing_error']['code'] == 'extraction_artifacts_missing'
        assert client.get(f"/books/{book['id']}/chapters").json()['chapters'] == []
    assert not (root() / 'books' / book['id'] / 'extracted').exists()


def test_upgrade_existing_m1_book_defaults_to_unprocessed():
    command.upgrade(migration_config(), '0001_books')
    engine = create_database_engine(database_path())
    book_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO books
            (id,title,original_filename,author,edition,year,page_count,imported_at,sha256,size_bytes)
            VALUES (:id,'Old','old.pdf',NULL,NULL,NULL,1,'2026-01-01T00:00:00Z',:sha,10)"""),
                           {'id': book_id, 'sha': 'a' * 64})
    engine.dispose()
    command.upgrade(migration_config(), 'head')
    engine = create_database_engine(database_path())
    assert sorted(inspect(engine).get_table_names()) == [
        'alembic_version', 'book_profiles', 'books', 'chapters', 'learning_goal_books',
        'learning_goals', 'pages']
    with Session(engine) as session:
        assert session.get(Book, book_id).processing_status == 'unprocessed'
    engine.dispose()


def test_processing_cors(library_client):
    response = library_client.options('/books/id/chapters', headers={
        'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'PUT'})
    assert response.status_code == 200

import asyncio
import tempfile
from uuid import uuid4

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from app.api.upload_form import upload_form
from app.config import database_path
from app.main import create_app
from app.services import pdf_inspection
from app.services.library_errors import LibraryError
from test_library import upload, root, assert_empty, fail


def test_truncated_and_malformed_uploads_close_spools(library_client, pdf_bytes, monkeypatch):
    spools = []
    original = tempfile.SpooledTemporaryFile
    def tracked(*args, **kwargs):
        spool = original(*args, **kwargs); spools.append(spool); return spool
    monkeypatch.setattr('starlette.formparsers.SpooledTemporaryFile', tracked)
    header = b'--x\r\nContent-Disposition: form-data; name="file"; filename="book.pdf"\r\n\r\n'
    for body in (header + pdf_bytes, header + pdf_bytes + b'\r\n--x\r\n', b'garbage\r\n'):
        response = library_client.post('/books', content=body, headers={'Content-Type': 'multipart/form-data; boundary=x'})
        assert response.status_code == 400
    assert spools and all(spool.closed for spool in spools)
    assert_empty(library_client)


def test_chunked_limit_ignores_declared_length_and_closes_spool(library_client, pdf_bytes, monkeypatch):
    from starlette.requests import Request
    from starlette.formparsers import MultiPartException
    from app.api.body_limit import UploadBodyLimit
    header = b'--x\r\nContent-Disposition: form-data; name="file"; filename="book.pdf"\r\n\r\n'
    monkeypatch.setattr('app.api.body_limit.MAX_REQUEST_BYTES', len(header) + 5)
    spools = []
    original = tempfile.SpooledTemporaryFile
    def tracked(*args, **kwargs):
        spool = original(*args, **kwargs); spools.append(spool); return spool
    monkeypatch.setattr('starlette.formparsers.SpooledTemporaryFile', tracked)
    for length_header in ([], [(b'content-length', b'1')]):
        scope = {'type': 'http', 'method': 'POST', 'path': '/books', 'headers': [
            (b'content-type', b'multipart/form-data; boundary=x'), *length_header]}
        messages = iter([{'type': 'http.request', 'body': header, 'more_body': True},
                         {'type': 'http.request', 'body': pdf_bytes, 'more_body': False}])
        async def receive():
            return next(messages)
        async def endpoint(scope, receive, send):
            async with upload_form(Request(scope, receive)):
                pytest.fail('Oversized request reached service')
        with pytest.raises(MultiPartException, match='Request body too large'):
            asyncio.run(UploadBodyLimit(endpoint)(scope, receive, None))
    assert len(spools) == 2 and all(s.closed for s in spools)


def test_disconnect_closes_partial_spool(monkeypatch):
    from starlette.requests import Request
    spools = []
    original = tempfile.SpooledTemporaryFile
    def tracked(*args, **kwargs):
        spool = original(*args, **kwargs); spools.append(spool); return spool
    monkeypatch.setattr('starlette.formparsers.SpooledTemporaryFile', tracked)
    messages = iter([
        {'type': 'http.request', 'body': b'--x\r\nContent-Disposition: form-data; name="file"; filename="a"\r\n\r\nbytes', 'more_body': True},
        {'type': 'http.disconnect'},
    ])
    async def receive():
        return next(messages)
    async def parse():
        async with upload_form(Request({'type': 'http', 'headers': [(b'content-type', b'multipart/form-data; boundary=x')]}, receive)):
            pytest.fail('Disconnected upload reached service')
    with pytest.raises(ClientDisconnect):
        asyncio.run(parse())
    assert spools and all(s.closed for s in spools)


def test_actual_repaired_pdf_rejected(library_client, pdf_bytes):
    damaged = pdf_bytes[:pdf_bytes.index(b'xref\n')]
    with pymupdf.open(stream=damaged, filetype='pdf') as doc:
        assert doc.is_repaired
    assert upload(library_client, damaged).status_code == 422
    assert_empty(library_client)


@pytest.mark.parametrize('kind', ['zero', 'page_failure'])
def test_structural_inspection_failures(library_client, pdf_bytes, monkeypatch, kind):
    class Document:
        is_pdf = True
        needs_pass = is_encrypted = is_repaired = False
        metadata = {}
        page_count = 0 if kind == 'zero' else 2
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def load_page(self, number): raise RuntimeError('Broken page tree')
    monkeypatch.setattr(pdf_inspection.pymupdf, 'open', lambda *args: Document())
    assert upload(library_client, pdf_bytes).status_code == 422
    assert_empty(library_client)


def test_pdf_no_extension_and_unusable_embedded_metadata(library_client):
    with pymupdf.open() as doc:
        doc.new_page()
        doc.set_metadata({'title': 'x'*501, 'author': 'a'*501, 'creationDate': 'D:20200101'})
        book = upload(library_client, doc.tobytes(), 'book.bin').json()
    assert book['title'] == 'book' and book['author'] is None and book['year'] is None


def test_filename_normalization_and_rejection():
    assert pdf_inspection.filename('a\\b\\c\x00.pdf') == 'c.pdf'
    for name in ('', '.', '..', 'a'*256):
        with pytest.raises(LibraryError):
            pdf_inspection.filename(name)


def test_delete_move_failure_keeps_book(library_client, pdf_bytes, monkeypatch):
    book = upload(library_client, pdf_bytes).json()
    with monkeypatch.context() as patch:
        patch.setattr(library_client.app.state.library.storage, 'move', fail)
        assert library_client.delete('/books/' + book['id']).status_code == 503
    assert library_client.get('/books/' + book['id']).json()['file_available']


def test_delete_uncertain_commit(library_client, pdf_bytes, monkeypatch):
    book = upload(library_client, pdf_bytes).json()
    commit = Session.commit
    def uncertain(session):
        commit(session); raise OSError('Uncertain commit')
    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', uncertain)
        assert library_client.delete('/books/' + book['id']).status_code == 503
    assert_empty(library_client)
    assert list((root() / '.trash').iterdir()) == []


def test_failed_restore_blocks_then_recovers(library_client, pdf_bytes, monkeypatch):
    book = upload(library_client, pdf_bytes).json()
    service = library_client.app.state.library
    move = service.storage.move
    def fail_restore(source, target, book_id):
        if source == '.trash': raise OSError('Restore failure')
        return move(source, target, book_id)
    with monkeypatch.context() as patch:
        patch.setattr(Session, 'commit', fail)
        patch.setattr(service.storage, 'move', fail_restore)
        assert library_client.delete('/books/' + book['id']).status_code == 503
        assert service.blocked and (root() / '.trash' / book['id']).exists()
        assert upload(library_client, pdf_bytes).status_code == 503
    assert upload(library_client, pdf_bytes).status_code == 409
    assert not service.blocked
    assert library_client.get('/books/' + book['id']).json()['file_available']


def test_failed_import_cleanup_and_database_unavailable(library_client, pdf_bytes, monkeypatch):
    service = library_client.app.state.library
    with monkeypatch.context() as patch:
        patch.setattr(service, 'ids', fail)
        response = upload(library_client, b'bad')
        assert response.status_code == 503 and service.blocked
        assert len(list((root() / '.staging').iterdir())) == 1
        assert upload(library_client, pdf_bytes).status_code == 503
    assert upload(library_client, pdf_bytes).status_code == 201
    assert list((root() / '.staging').iterdir()) == []


def test_recovery_conflict_preserves_both(migrated, pdf_bytes):
    with TestClient(create_app()) as client:
        book = upload(client, pdf_bytes).json()
    trash = root() / '.trash' / book['id']; trash.mkdir(); (trash / 'original.pdf').write_bytes(pdf_bytes)
    with TestClient(create_app()) as client:
        assert client.get('/books').status_code == 503
    assert trash.exists() and (root() / 'books' / book['id']).exists()


def test_wrong_revision_does_not_cleanup(migrated, pdf_bytes):
    with TestClient(create_app()) as client:
        with client.app.state.database_engine.begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num='old'"))
    stage = root() / '.staging' / str(uuid4()); stage.mkdir(); (stage / 'original.pdf').write_bytes(pdf_bytes)
    with TestClient(create_app()) as client:
        assert client.get('/books').json()['error']['code'] == 'library_setup_required'
    assert stage.exists()


def test_spool_io_failure_is_safe_storage_error(library_client, pdf_bytes, monkeypatch):
    monkeypatch.setattr('starlette.formparsers.SpooledTemporaryFile', fail)
    response = upload(library_client, pdf_bytes)
    assert response.status_code == 503 and 'private' not in response.text
    assert_empty(library_client)


def test_symlinked_managed_directory_blocks_recovery(migrated, tmp_path):
    outside = tmp_path / 'outside'; outside.mkdir(); (outside / 'keep').write_text('keep')
    (root() / 'books').symlink_to(outside, target_is_directory=True)
    with TestClient(create_app()) as client:
        assert client.get('/books').status_code == 503
    assert (outside / 'keep').read_text() == 'keep'


def test_list_ties_sort_by_id(library_client, pdf_bytes):
    first = upload(library_client, pdf_bytes).json()
    with pymupdf.open(stream=pdf_bytes) as doc:
        doc.new_page()
        second = upload(library_client, doc.tobytes()).json()
    with library_client.app.state.database_engine.begin() as connection:
        connection.execute(text('UPDATE books SET imported_at=:stamp'), {'stamp': '2026-09-18T00:00:00.000000Z'})
    assert [b['id'] for b in library_client.get('/books').json()['books']] == sorted([first['id'], second['id']])

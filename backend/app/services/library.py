import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.schemas.book import BookResponse
from app.services.library_errors import LibraryError, storage_error
from app.services.library_storage import Storage, sync_directory
from app.services.pdf_inspection import filename, inspect_pdf, metadata_fields

MAX_FILE_BYTES = 100 * 1024 * 1024


class Library:
    def __init__(self, engine, root):
        self.engine = engine
        self.storage = Storage(root)
        self.lock = RLock()
        self.blocked = False
        self.recover()

    def ids(self):
        with self.engine.connect() as connection:
            return set(connection.scalars(select(Book.id)))

    def recover(self):
        # Read committed state and validate ALL entries before any destructive work.
        ids = self.ids()
        entries = {area: self.storage.entries(area) for area in ('books', '.staging', '.trash')}
        for path in entries['.trash']:
            if self.storage.path('books', path.name).exists():
                raise OSError('Conflicting recovery directories')
        for path in entries['.trash']:
            if path.name in ids:
                self.storage.move('.trash', 'books', path.name)
            else:
                self.storage.remove('.trash', path.name)
        for path in entries['.staging']:
            self.storage.remove('.staging', path.name)
        for path in entries['books']:
            if path.name not in ids:
                self.storage.remove('books', path.name)
        self.blocked = False

    def view(self, book):
        values = {key: getattr(book, key) for key in BookResponse.model_fields if key != 'file_available'}
        return BookResponse(**values, file_available=self.storage.available(book.id)).model_dump()

    def list_books(self):
        with self.lock, Session(self.engine) as session:
            return {'books': [self.view(b) for b in session.scalars(
                select(Book).order_by(Book.imported_at.desc(), Book.id.asc()))]}

    def details(self, book_id):
        with self.lock, Session(self.engine) as session:
            book = session.get(Book, book_id)
            if book is None:
                raise LibraryError(404, 'book_not_found', 'Book not found.')
            return self.view(book)

    def allow_mutation(self):
        if self.blocked:
            self.recover()

    def import_book(self, upload, fields):
        with self.lock:
            self.allow_mutation()
            original = filename(upload.filename)
            values = metadata_fields(fields)
            book_id = str(uuid4())
            # Never clean an existing directory if UUID allocation collides.
            stage = self.storage.create_stage(book_id)
            try:
                digest, size = hashlib.sha256(), 0
                with (stage / 'original.pdf').open('xb') as output:
                    while chunk := upload.file.read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_FILE_BYTES:
                            raise LibraryError(413, 'file_too_large', 'PDF must be at most 100 MiB.')
                        digest.update(chunk)
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
                sync_directory(stage)
                if size == 0:
                    raise LibraryError(422, 'empty_pdf', 'The selected PDF is empty.')
                inspected = inspect_pdf(stage / 'original.pdf')
                with Session(self.engine) as session:
                    existing = session.scalar(select(Book).where(Book.sha256 == digest.hexdigest()))
                    if existing:
                        raise LibraryError(409, 'duplicate_book', 'This PDF is already in your library.',
                                           existing_book_id=existing.id)
                    book = Book(id=book_id, original_filename=original,
                                title=values['title'] or inspected['title'] or Path(original).stem or original,
                                author=values['author'] or inspected['author'], edition=values['edition'],
                                year=values['year'], page_count=inspected['page_count'],
                                imported_at=datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
                                sha256=digest.hexdigest(), size_bytes=size)
                    session.add(book)
                    session.flush()
                    self.storage.move('.staging', 'books', book_id)
                    session.commit()
                return self.details(book_id)
            except Exception:
                try:
                    # A fresh read handles commit-success/response-failure ambiguity.
                    if book_id not in self.ids():
                        self.storage.remove('books', book_id)
                        self.storage.remove('.staging', book_id)
                except Exception as cleanup:
                    self.blocked = True
                    raise storage_error() from cleanup
                raise

    def delete(self, book_id):
        with self.lock:
            # Permit an explicit cleanup retry to acknowledge this exact deletion.
            pending = self.storage.path('.trash', book_id).exists()
            self.allow_mutation()
            try:
                with Session(self.engine) as session:
                    book = session.get(Book, book_id)
                    if book is None:
                        if pending:
                            self.storage.remove('.trash', book_id)
                            return
                        raise LibraryError(404, 'book_not_found', 'Book not found.')
                    if self.storage.path('books', book_id).exists():
                        self.storage.move('books', '.trash', book_id)
                    session.delete(book)
                    session.commit()
            except LibraryError:
                raise
            except Exception:
                try:
                    if book_id in self.ids():
                        if self.storage.path('.trash', book_id).exists():
                            self.storage.move('.trash', 'books', book_id)
                    else:
                        self.storage.remove('.trash', book_id)
                except Exception as cleanup:
                    self.blocked = True
                    raise storage_error() from cleanup
                raise
            try:
                self.storage.remove('.trash', book_id)
            except Exception as exc:
                self.blocked = True
                raise LibraryError(503, 'deletion_cleanup_pending',
                                   'The book record was removed, but file cleanup is pending. Retry deletion.') from exc

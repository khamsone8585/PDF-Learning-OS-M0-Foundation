from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.book import Book, Chapter, Page
from app.services.library_errors import LibraryError, storage_error
from app.services.pdf_inspection import clean_text
from app.services.pdf_processing import extract_pdf, write_pages


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


class PDFProcessingService:
    def __init__(self, library):
        self.library = library
        self.engine = library.engine
        self.storage = library.storage

    def _book(self, session, book_id):
        book = session.get(Book, book_id)
        if book is None:
            raise LibraryError(404, 'book_not_found', 'Book not found.')
        return book

    def _record_failure(self, book_id, code, message):
        with self.library.lock, Session(self.engine) as session:
            book = session.get(Book, book_id)
            if book is not None and book.processing_status == 'processing':
                book.processing_status = 'failed'
                book.processing_error_code = code
                book.processing_error_message = message
                session.commit()

    def _cleanup_attempt(self, book_id, attempt_id):
        try:
            self.storage.remove_processing(book_id, attempt_id)
            self.storage.remove_generation(book_id, attempt_id)
        except Exception as exc:
            self.library.blocked = True
            raise storage_error() from exc

    def process(self, book_id):
        attempt_id = str(uuid4())
        with self.library.lock, Session(self.engine) as session:
            self.library.allow_mutation()
            book = self._book(session, book_id)
            if book.processing_status == 'processing':
                raise LibraryError(409, 'processing_in_progress', 'This PDF is already being processed.')
            if not self.storage.available(book_id):
                raise LibraryError(409, 'source_file_missing',
                                   'The original PDF is missing. Restore it before processing.')
            expected_sha256, expected_pages = book.sha256, book.page_count
            old_generation = book.active_extraction_id
            book.processing_status = 'processing'
            book.processing_error_code = None
            book.processing_error_message = None
            book.processing_started_at = timestamp()
            session.commit()

        final_created = False
        try:
            attempt = self.storage.create_processing(book_id, attempt_id)
            extraction = extract_pdf(self.storage.path('books', book_id) / 'original.pdf',
                                     expected_sha256, expected_pages)
            page_records = write_pages(attempt, extraction.pages)
            self.storage.finish_processing(book_id, attempt_id)
            final_created = True

            commit_error = None
            try:
                with self.library.lock, Session(self.engine) as session:
                    book = self._book(session, book_id)
                    if book.processing_status != 'processing':
                        raise LibraryError(409, 'processing_interrupted',
                                           'Processing state changed. Try again.')
                    existing_source = session.scalar(
                        select(Chapter.source).where(Chapter.book_id == book_id)
                        .order_by(Chapter.position).limit(1))
                    session.execute(delete(Page).where(Page.book_id == book_id))
                    for number, count, digest in page_records:
                        session.add(Page(book_id=book_id, page_number=number,
                                         char_count=count, text_sha256=digest))
                    if existing_source != 'manual':
                        session.execute(delete(Chapter).where(Chapter.book_id == book_id))
                        for position, draft in enumerate(extraction.chapters):
                            session.add(Chapter(id=str(uuid4()), book_id=book_id, position=position,
                                                title=draft.title, level=draft.level,
                                                start_page=draft.start_page, end_page=draft.end_page,
                                                source=draft.source))
                    book.active_extraction_id = attempt_id
                    book.toc_status = extraction.toc_status
                    book.processing_status = 'processed'
                    book.processing_error_code = None
                    book.processing_error_message = None
                    book.processed_at = timestamp()
                    session.commit()
            except Exception as exc:
                commit_error = exc

            with Session(self.engine) as session:
                committed = session.scalar(select(Book.active_extraction_id).where(Book.id == book_id)) == attempt_id
            if not committed:
                self._cleanup_attempt(book_id, attempt_id)
                if isinstance(commit_error, LibraryError):
                    raise commit_error
                raise storage_error() from commit_error
            if old_generation and old_generation != attempt_id:
                try:
                    self.storage.remove_generation(book_id, old_generation)
                except Exception as exc:
                    self.library.blocked = True
                    raise LibraryError(503, 'processing_cleanup_pending',
                                       'Processing completed, but old-file cleanup is pending. Retry later.') from exc
            return self.library.details(book_id)
        except LibraryError as exc:
            current = None
            with Session(self.engine) as session:
                current = session.scalar(select(Book.active_extraction_id).where(Book.id == book_id))
            if current != attempt_id:
                self._cleanup_attempt(book_id, attempt_id)
                error = exc.body['error']
                self._record_failure(book_id, error['code'], error['message'])
            raise
        except Exception as exc:
            try:
                if final_created:
                    with Session(self.engine) as session:
                        current = session.scalar(select(Book.active_extraction_id).where(Book.id == book_id))
                    if current != attempt_id:
                        self._cleanup_attempt(book_id, attempt_id)
                else:
                    self._cleanup_attempt(book_id, attempt_id)
                self._record_failure(book_id, 'processing_failed',
                                     'PDF processing failed. Try processing the PDF again.')
            except LibraryError:
                raise
            raise storage_error() from exc

    def chapters(self, book_id):
        with self.library.lock, Session(self.engine) as session:
            book = self._book(session, book_id)
            chapters = list(session.scalars(select(Chapter).where(Chapter.book_id == book_id)
                                            .order_by(Chapter.position)))
            return {
                'book_id': book_id,
                'processing_status': book.processing_status,
                'content_available': book.active_extraction_id is not None,
                'toc_status': book.toc_status,
                'structure_source': chapters[0].source if chapters else None,
                'chapters': [{key: getattr(chapter, key) for key in
                              ('id', 'title', 'position', 'level', 'start_page', 'end_page', 'source')}
                             for chapter in chapters],
            }

    def correct_chapters(self, book_id, sections):
        with self.library.lock, Session(self.engine) as session:
            self.library.allow_mutation()
            book = self._book(session, book_id)
            if book.processing_status == 'processing':
                raise LibraryError(409, 'processing_in_progress',
                                   'Wait for PDF processing to finish before changing sections.')
            if book.processing_status != 'processed' or book.active_extraction_id is None:
                raise LibraryError(409, 'book_not_processed', 'Process this PDF before changing sections.')
            existing = list(session.scalars(select(Chapter).where(Chapter.book_id == book_id)
                                            .order_by(Chapter.position)))
            if not existing or existing[0].source not in ('fallback', 'manual'):
                raise LibraryError(409, 'toc_structure_not_editable',
                                   'PDF bookmark structure is read-only in M2.')
            values = []
            for section in sections:
                title = clean_text(section.title)
                if not title or len(title) > 500:
                    raise LibraryError(422, 'invalid_chapter_structure',
                                       'Each section needs a title of 1–500 characters.', field='sections')
                values.append((title, section.start_page))
            starts = [start for _title, start in values]
            if starts[0] != 1 or starts != sorted(set(starts)) or starts[-1] > book.page_count:
                raise LibraryError(422, 'invalid_chapter_structure',
                                   'Section pages must start at 1 and increase within the book.', field='sections')
            session.execute(delete(Chapter).where(Chapter.book_id == book_id))
            for position, (title, start) in enumerate(values):
                end = values[position + 1][1] - 1 if position + 1 < len(values) else book.page_count
                session.add(Chapter(id=str(uuid4()), book_id=book_id, position=position, title=title,
                                    level=1, start_page=start, end_page=end, source='manual'))
            session.commit()
        return self.chapters(book_id)

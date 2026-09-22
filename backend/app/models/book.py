from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = 'books'
    __table_args__ = (
        UniqueConstraint('sha256', name='uq_books_sha256'),
        CheckConstraint('page_count > 0', name='positive_pages'),
        CheckConstraint('size_bytes > 0 AND size_bytes <= 104857600', name='bounded_size'),
        CheckConstraint('year IS NULL OR (year >= 1 AND year <= 9999)', name='valid_year'),
        CheckConstraint('length(title) BETWEEN 1 AND 500', name='title_length'),
        CheckConstraint('length(original_filename) BETWEEN 1 AND 255', name='filename_length'),
        CheckConstraint('author IS NULL OR length(author) <= 500', name='author_length'),
        CheckConstraint('edition IS NULL OR length(edition) <= 100', name='edition_length'),
        CheckConstraint("length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'", name='valid_digest'),
        CheckConstraint("processing_status IN ('unprocessed', 'processing', 'processed', 'failed')",
                        name='valid_processing_status'),
        CheckConstraint("toc_status IS NULL OR toc_status IN ('available', 'partial', 'missing', 'invalid')",
                        name='valid_toc_status'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(500))
    edition: Mapped[str | None] = mapped_column(String(100))
    year: Mapped[int | None] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[str] = mapped_column(String(32))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    processing_status: Mapped[str] = mapped_column(String(16), default='unprocessed', server_default='unprocessed')
    processing_error_code: Mapped[str | None] = mapped_column(String(64))
    processing_error_message: Mapped[str | None] = mapped_column(String(500))
    processing_started_at: Mapped[str | None] = mapped_column(String(32))
    processed_at: Mapped[str | None] = mapped_column(String(32))
    active_extraction_id: Mapped[str | None] = mapped_column(String(36))
    toc_status: Mapped[str | None] = mapped_column(String(16))


class Page(Base):
    __tablename__ = 'pages'
    __table_args__ = (
        CheckConstraint('page_number > 0', name='positive_page_number'),
        CheckConstraint('char_count >= 0', name='nonnegative_char_count'),
        CheckConstraint("length(text_sha256) = 64 AND text_sha256 NOT GLOB '*[^0-9a-f]*'",
                        name='valid_text_digest'),
    )
    book_id: Mapped[str] = mapped_column(String(36), ForeignKey('books.id', ondelete='CASCADE'), primary_key=True)
    page_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    char_count: Mapped[int] = mapped_column(Integer)
    text_sha256: Mapped[str] = mapped_column(String(64))


class Chapter(Base):
    __tablename__ = 'chapters'
    __table_args__ = (
        UniqueConstraint('book_id', 'position', name='uq_chapters_book_position'),
        CheckConstraint('position >= 0', name='nonnegative_chapter_position'),
        CheckConstraint('length(title) BETWEEN 1 AND 500', name='chapter_title_length'),
        CheckConstraint('level > 0', name='positive_chapter_level'),
        CheckConstraint('start_page > 0 AND end_page >= start_page', name='valid_chapter_range'),
        CheckConstraint("source IN ('toc', 'fallback', 'manual')", name='valid_chapter_source'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    book_id: Mapped[str] = mapped_column(String(36), ForeignKey('books.id', ondelete='CASCADE'))
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    level: Mapped[int] = mapped_column(Integer)
    start_page: Mapped[int] = mapped_column(Integer)
    end_page: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))

from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
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

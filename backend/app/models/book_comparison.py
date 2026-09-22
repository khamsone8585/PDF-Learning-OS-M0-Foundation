from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.book import Base


class BookComparison(Base):
    __tablename__ = 'book_comparisons'
    __table_args__ = (
        CheckConstraint('revision > 0', name='comparison_positive_revision'),
        CheckConstraint("length(input_fingerprint) = 64 AND input_fingerprint NOT GLOB '*[^0-9a-f]*'",
                        name='comparison_fingerprint'),
    )
    goal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('learning_goals.id', ondelete='CASCADE'), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    algorithm_version: Mapped[str] = mapped_column(String(32))
    snapshot_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))


class BookComparisonBook(Base):
    __tablename__ = 'book_comparison_books'
    goal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('book_comparisons.goal_id', ondelete='CASCADE'), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('books.id', ondelete='CASCADE'), primary_key=True)

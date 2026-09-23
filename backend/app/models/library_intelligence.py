from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.book import Base


class CurriculumTriage(Base):
    __tablename__ = 'curriculum_triages'
    __table_args__ = (
        CheckConstraint('length(title) BETWEEN 1 AND 200', name='triage_title_length'),
        CheckConstraint('description IS NULL OR length(description) <= 2000',
                        name='triage_description_length'),
        CheckConstraint('target_domain IS NULL OR length(target_domain) BETWEEN 1 AND 200',
                        name='triage_domain_length'),
        CheckConstraint("difficulty_ceiling IS NULL OR difficulty_ceiling IN "
                        "('beginner','intermediate','advanced')", name='triage_difficulty'),
        CheckConstraint("scope_kind IN ('library_snapshot','selected')", name='triage_scope'),
        CheckConstraint("status IN ('draft','applied','archived','invalidated')", name='triage_status'),
        CheckConstraint('revision > 0', name='triage_positive_revision'),
        CheckConstraint("length(scope_fingerprint)=64 AND scope_fingerprint NOT GLOB '*[^0-9a-f]*'",
                        name='triage_scope_fingerprint'),
        CheckConstraint("length(input_fingerprint)=64 AND input_fingerprint NOT GLOB '*[^0-9a-f]*'",
                        name='triage_input_fingerprint'),
        Index('uq_curriculum_triages_single_draft', 'status', unique=True,
              sqlite_where=text("status = 'draft'")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(2000))
    target_domain: Mapped[str | None] = mapped_column(String(200))
    target_topics_json: Mapped[str] = mapped_column(Text)
    difficulty_ceiling: Mapped[str | None] = mapped_column(String(16))
    scope_kind: Mapped[str] = mapped_column(String(20))
    revision: Mapped[int] = mapped_column(Integer)
    scope_fingerprint: Mapped[str] = mapped_column(String(64))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    algorithm_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    applied_goal_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey('learning_goals.id', ondelete='SET NULL'), unique=True)
    created_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))
    applied_at: Mapped[str | None] = mapped_column(String(32))


class CurriculumTriageBook(Base):
    __tablename__ = 'curriculum_triage_books'
    triage_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('curriculum_triages.id', ondelete='CASCADE'), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('books.id', ondelete='CASCADE'), primary_key=True)


class LibraryRelationReview(Base):
    __tablename__ = 'library_relation_reviews'
    __table_args__ = (
        CheckConstraint('left_book_id < right_book_id', name='relation_sorted_pair'),
        CheckConstraint("decision IN ('same_work','related_edition','distinct')",
                        name='relation_decision'),
        CheckConstraint("(decision='same_work' AND preferred_book_id IS NOT NULL) OR "
                        "(decision<>'same_work' AND preferred_book_id IS NULL)",
                        name='relation_preferred_coherence'),
        CheckConstraint('preferred_book_id IS NULL OR preferred_book_id=left_book_id OR '
                        'preferred_book_id=right_book_id', name='relation_preferred_member'),
        CheckConstraint('note IS NULL OR length(note) <= 1000', name='relation_note_length'),
    )
    left_book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('books.id', ondelete='CASCADE'), primary_key=True)
    right_book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('books.id', ondelete='CASCADE'), primary_key=True)
    decision: Mapped[str] = mapped_column(String(20))
    preferred_book_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey('books.id', ondelete='CASCADE'))
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))

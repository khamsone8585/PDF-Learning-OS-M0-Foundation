from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.book import Base

SOURCES = "'manual', 'ai_generated', 'ai_assisted', 'derived'"


class BookProfile(Base):
    __tablename__ = 'book_profiles'
    __table_args__ = (
        CheckConstraint('domain IS NULL OR length(domain) BETWEEN 1 AND 200',
                        name='book_profile_domain_length'),
        CheckConstraint("difficulty IS NULL OR difficulty IN ('beginner', 'intermediate', 'advanced')",
                        name='book_profile_difficulty'),
        CheckConstraint("orientation IS NULL OR orientation IN ('theory_heavy', 'balanced', 'practice_heavy')",
                        name='book_profile_orientation'),
        CheckConstraint('suggested_use IS NULL OR length(suggested_use) BETWEEN 1 AND 2000',
                        name='book_profile_suggested_use_length'),
        *(CheckConstraint(f'{field}_source IS NULL OR {field}_source IN ({SOURCES})',
                          name=f'book_profile_{field}_source')
          for field in ('domain', 'difficulty', 'prerequisites', 'main_topics', 'orientation',
                        'strengths', 'weaknesses', 'suggested_use')),
        *(CheckConstraint(
            f'({field} IS NULL AND {field}_source IS NULL) OR '
            f'({field} IS NOT NULL AND {field}_source IS NOT NULL)',
            name=f'book_profile_{field}_source_coherence')
          for field in ('domain', 'difficulty', 'orientation', 'suggested_use')),
        *(CheckConstraint(
            f"({field}_json = '[]' AND {field}_source IS NULL) OR "
            f"({field}_json <> '[]' AND {field}_source IS NOT NULL)",
            name=f'book_profile_{field}_source_coherence')
          for field in ('prerequisites', 'main_topics', 'strengths', 'weaknesses')),
    )
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('books.id', ondelete='CASCADE'), primary_key=True)
    domain: Mapped[str | None] = mapped_column(String(200))
    difficulty: Mapped[str | None] = mapped_column(String(16))
    prerequisites_json: Mapped[str] = mapped_column(Text, default='[]', server_default='[]')
    main_topics_json: Mapped[str] = mapped_column(Text, default='[]', server_default='[]')
    orientation: Mapped[str | None] = mapped_column(String(20))
    strengths_json: Mapped[str] = mapped_column(Text, default='[]', server_default='[]')
    weaknesses_json: Mapped[str] = mapped_column(Text, default='[]', server_default='[]')
    suggested_use: Mapped[str | None] = mapped_column(Text)
    domain_source: Mapped[str | None] = mapped_column(String(16))
    difficulty_source: Mapped[str | None] = mapped_column(String(16))
    prerequisites_source: Mapped[str | None] = mapped_column(String(16))
    main_topics_source: Mapped[str | None] = mapped_column(String(16))
    orientation_source: Mapped[str | None] = mapped_column(String(16))
    strengths_source: Mapped[str | None] = mapped_column(String(16))
    weaknesses_source: Mapped[str | None] = mapped_column(String(16))
    suggested_use_source: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))

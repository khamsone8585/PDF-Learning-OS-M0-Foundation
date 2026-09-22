from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.book import Base


class LearningGoal(Base):
    __tablename__ = 'learning_goals'
    __table_args__ = (
        CheckConstraint('length(title) BETWEEN 1 AND 200', name='learning_goal_title_length'),
        CheckConstraint('description IS NULL OR length(description) <= 2000',
                        name='learning_goal_description_length'),
        CheckConstraint('is_active IN (0, 1)', name='learning_goal_active_boolean'),
        Index('uq_learning_goals_single_active', 'is_active', unique=True,
              sqlite_where=text('is_active = 1')),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(2000))
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))


class LearningGoalBook(Base):
    __tablename__ = 'learning_goal_books'
    goal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('learning_goals.id', ondelete='CASCADE'), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('books.id', ondelete='CASCADE'), primary_key=True)

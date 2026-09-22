from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.learning_goal import LearningGoal, LearningGoalBook
from app.services.library_errors import LibraryError


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def canonical_goal_id(value):
    try:
        if str(UUID(value)) == value:
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    raise LibraryError(422, 'invalid_id', 'A canonical learning goal UUID is required.',
                       field='goal_id')


class LearningGoalService:
    def __init__(self, library):
        self.library = library
        self.engine = library.engine
        self.lock = library.lock

    def _text(self, title, description):
        title = title.strip()
        if not title or len(title) > 200:
            raise LibraryError(422, 'invalid_goal_title',
                               'Goal title must contain 1–200 characters.')
        description = description.strip() if description is not None else None
        if description == '':
            description = None
        if description is not None and len(description) > 2000:
            raise LibraryError(422, 'invalid_goal_description',
                               'Goal description must contain at most 2,000 characters.')
        return title, description

    def _books(self, session, book_ids):
        if not 3 <= len(book_ids) <= 5:
            raise LibraryError(422, 'invalid_book_selection',
                               'Select between 3 and 5 books.')
        canonical = []
        for value in book_ids:
            try:
                valid = str(UUID(value))
            except (ValueError, TypeError, AttributeError) as exc:
                raise LibraryError(422, 'invalid_book_id',
                                   'Every selected book ID must be a canonical UUID.') from exc
            if valid != value:
                raise LibraryError(422, 'invalid_book_id',
                                   'Every selected book ID must be a canonical UUID.')
            canonical.append(valid)
        if len(set(canonical)) != len(canonical):
            raise LibraryError(422, 'duplicate_book_ids',
                               'Select each book only once.')
        existing = set(session.scalars(select(Book.id).where(Book.id.in_(canonical))))
        missing = sorted(set(canonical) - existing)
        if missing:
            raise LibraryError(404, 'books_not_found',
                               'One or more selected books were not found.',
                               missing_book_ids=missing)
        return sorted(canonical)

    def _view(self, session, goal):
        book_ids = list(session.scalars(select(LearningGoalBook.book_id).where(
            LearningGoalBook.goal_id == goal.id).order_by(LearningGoalBook.book_id)))
        return {
            'id': goal.id, 'title': goal.title, 'description': goal.description,
            'is_active': goal.is_active, 'created_at': goal.created_at,
            'updated_at': goal.updated_at, 'book_ids': book_ids,
        }

    def active(self):
        with self.lock, Session(self.engine) as session:
            goal = session.scalar(select(LearningGoal).where(LearningGoal.is_active.is_(True)))
            return {'goal': self._view(session, goal) if goal else None}

    def create(self, title, description, book_ids):
        title, description = self._text(title, description)
        with self.lock:
            self.library.allow_mutation()
            with Session(self.engine) as session:
                selected = self._books(session, book_ids)
                timestamp = utc_now()
                previous = session.scalar(select(LearningGoal).where(LearningGoal.is_active.is_(True)))
                if previous:
                    previous.is_active = False
                    previous.updated_at = timestamp
                    session.flush()
                goal = LearningGoal(id=str(uuid4()), title=title, description=description,
                                    is_active=True, created_at=timestamp, updated_at=timestamp)
                session.add(goal)
                session.add_all(LearningGoalBook(goal_id=goal.id, book_id=book_id)
                                for book_id in selected)
                session.commit()
                return self._view(session, goal)

    def replace_books(self, goal_id, book_ids):
        with self.lock:
            self.library.allow_mutation()
            with Session(self.engine) as session:
                goal = session.get(LearningGoal, goal_id)
                if goal is None:
                    raise LibraryError(404, 'goal_not_found', 'Learning goal not found.')
                if not goal.is_active:
                    raise LibraryError(409, 'goal_inactive',
                                       'Only the active learning goal can be changed.')
                selected = self._books(session, book_ids)
                session.execute(delete(LearningGoalBook).where(
                    LearningGoalBook.goal_id == goal.id))
                session.add_all(LearningGoalBook(goal_id=goal.id, book_id=book_id)
                                for book_id in selected)
                goal.updated_at = utc_now()
                session.commit()
                return self._view(session, goal)

import json

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.book_profile import BookProfile
from app.services.learning_goals import utc_now
from app.services.library_errors import LibraryError, storage_error

LIST_RULES = {
    'prerequisites': (25, 200),
    'main_topics': (50, 200),
    'strengths': (20, 500),
    'weaknesses': (20, 500),
}
SCALARS = ('domain', 'difficulty', 'orientation', 'suggested_use')
FIELDS = (*SCALARS[:2], 'prerequisites', 'main_topics', SCALARS[2], 'strengths',
          'weaknesses', SCALARS[3])


class BookProfileService:
    def __init__(self, library):
        self.library = library
        self.engine = library.engine
        self.lock = library.lock

    @staticmethod
    def _scalar(value, field, maximum):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > maximum:
            raise LibraryError(422, f'invalid_{field}',
                               f'{field.replace("_", " ").title()} must contain at most {maximum:,} characters.')
        return value

    @staticmethod
    def _items(values, field):
        maximum, item_maximum = LIST_RULES[field]
        if len(values) > maximum:
            raise LibraryError(422, f'invalid_{field}',
                               f'{field.replace("_", " ").title()} may contain at most {maximum} items.')
        result = []
        seen = set()
        for value in values:
            item = value.strip()
            if not item or len(item) > item_maximum:
                raise LibraryError(422, f'invalid_{field}',
                                   f'Each {field.replace("_", " ")} item must contain 1–{item_maximum} characters.')
            key = item.casefold()
            if key in seen:
                raise LibraryError(422, f'duplicate_{field}',
                                   f'{field.replace("_", " ").title()} must not contain duplicates.')
            seen.add(key)
            result.append(item)
        return result

    def _normalize(self, body):
        values = {
            'domain': self._scalar(body.domain, 'domain', 200),
            'difficulty': body.difficulty,
            'prerequisites': self._items(body.prerequisites, 'prerequisites'),
            'main_topics': self._items(body.main_topics, 'main_topics'),
            'orientation': body.orientation,
            'strengths': self._items(body.strengths, 'strengths'),
            'weaknesses': self._items(body.weaknesses, 'weaknesses'),
            'suggested_use': self._scalar(body.suggested_use, 'suggested_use', 2000),
        }
        if not any(values[field] for field in FIELDS):
            raise LibraryError(422, 'empty_book_profile',
                               'Enter at least one book profile field.')
        return values

    @staticmethod
    def _decode(value):
        try:
            decoded = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise storage_error() from exc
        if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
            raise storage_error()
        return decoded

    def _view(self, profile):
        values = {
            'domain': profile.domain,
            'difficulty': profile.difficulty,
            'prerequisites': self._decode(profile.prerequisites_json),
            'main_topics': self._decode(profile.main_topics_json),
            'orientation': profile.orientation,
            'strengths': self._decode(profile.strengths_json),
            'weaknesses': self._decode(profile.weaknesses_json),
            'suggested_use': profile.suggested_use,
        }
        return {
            'book_id': profile.book_id,
            **values,
            'provenance': {field: getattr(profile, f'{field}_source') for field in FIELDS},
            'created_at': profile.created_at,
            'updated_at': profile.updated_at,
        }

    def get(self, book_id):
        with self.lock, Session(self.engine) as session:
            if session.get(Book, book_id) is None:
                raise LibraryError(404, 'book_not_found', 'Book not found.')
            profile = session.get(BookProfile, book_id)
            return {'profile': self._view(profile) if profile else None}

    def put(self, book_id, body):
        values = self._normalize(body)
        with self.lock:
            self.library.allow_mutation()
            with Session(self.engine) as session:
                if session.get(Book, book_id) is None:
                    raise LibraryError(404, 'book_not_found', 'Book not found.')
                timestamp = utc_now()
                profile = session.get(BookProfile, book_id)
                if profile is None:
                    profile = BookProfile(book_id=book_id, created_at=timestamp, updated_at=timestamp)
                    session.add(profile)
                for field in SCALARS:
                    setattr(profile, field, values[field])
                for field in LIST_RULES:
                    setattr(profile, f'{field}_json', json.dumps(
                        values[field], ensure_ascii=False, separators=(',', ':')))
                for field in FIELDS:
                    setattr(profile, f'{field}_source', 'manual' if values[field] else None)
                profile.updated_at = timestamp
                session.commit()
                return self._view(profile)

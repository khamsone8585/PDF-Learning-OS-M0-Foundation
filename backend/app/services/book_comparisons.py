"""Goal-scoped, profile-only comparisons. Never reads PDF content."""
import hashlib
from itertools import combinations

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.book_profile import BookProfile
from app.models.book_comparison import BookComparison, BookComparisonBook
from app.models.learning_goal import LearningGoal, LearningGoalBook
from app.schemas.book_comparison import ComparisonPreview, ComparisonRequest, ComparisonSnapshot
from app.schemas.book_profile import BookProfileResponse
from app.services.book_profiles import BookProfileService
from app.services.learning_goals import utc_now
from app.services.library_errors import LibraryError, storage_error
from app.services.profile_matching import canonical_json, keys, normalize, set_comparison

ALGORITHM = 'profile_exact_v1'
DIFFICULTY = {'beginner': 0, 'intermediate': 1, 'advanced': 2}


def compare(goal, books):
    coverage = [{'topic': topic, 'book_ids': [book['book_id'] for book in books
                 if topic in book['topic_keys']]}
                for topic in sorted({topic for book in books for topic in book['topic_keys']})]
    for book in books:
        book['topic_count'] = len(book['topic_keys'])
        book['unique_topics'] = [item['topic'] for item in coverage
                                 if item['book_ids'] == [book['book_id']]]
    pairs = []
    for left, right in combinations(books, 2):
        lp, rp = left['profile'], right['profile']
        difficulty = 'unknown'
        if lp['difficulty'] is not None and rp['difficulty'] is not None:
            difference = DIFFICULTY[lp['difficulty']] - DIFFICULTY[rp['difficulty']]
            difficulty = 'same' if difference == 0 else 'lower' if difference < 0 else 'higher'
        pairs.append({
            'left_book_id': left['book_id'], 'right_book_id': right['book_id'],
            'overlap': set_comparison(left['topic_keys'], right['topic_keys']),
            'difficulty': difficulty,
            'prerequisites': set_comparison(keys(lp['prerequisites']), keys(rp['prerequisites']))
            if lp['prerequisites'] and rp['prerequisites'] else None,
        })
    return ComparisonPreview.model_validate({
        'goal': goal, 'books': books, 'coverage': coverage, 'pairs': pairs,
        'algorithm_version': ALGORITHM, 'derived_source': 'derived',
    }).model_dump()


class BookComparisonService:
    def __init__(self, library):
        self.library = library
        self.engine = library.engine
        self.lock = library.lock
        self.profiles = BookProfileService(library)

    def _inputs(self, session, goal):
        ids = list(session.scalars(select(LearningGoalBook.book_id).where(
            LearningGoalBook.goal_id == goal.id).order_by(LearningGoalBook.book_id)))
        issues, books = [], []
        if not goal.is_active:
            issues.append({'code': 'goal_inactive', 'message': 'Only the active goal can be compared.'})
        if not 3 <= len(ids) <= 5:
            issues.append({'code': 'invalid_book_selection', 'message': 'Select between 3 and 5 books.'})
        for book_id in ids:
            book = session.get(Book, book_id)
            profile = session.get(BookProfile, book_id)
            code = 'book_missing' if book is None else 'profile_missing' if profile is None else None
            if code:
                issues.append({'code': code, 'book_id': book_id,
                               'message': 'Book not found.' if book is None else 'Record a book profile.'})
                continue
            try:
                view = BookProfileResponse.model_validate(self.profiles._view(profile)).model_dump()
            except (ValidationError, ValueError) as exc:
                raise storage_error() from exc
            topics = keys(view['main_topics'])
            if not topics:
                issues.append({'code': 'topics_missing', 'book_id': book_id,
                               'message': 'Record at least one main topic.'})
            books.append({'book_id': book_id, 'title': book.title, 'profile': view,
                          'topic_keys': topics})
        goal_input = {'id': goal.id, 'title': goal.title, 'description': goal.description,
                      'updated_at': goal.updated_at, 'book_ids': ids}
        raw = {'goal': goal_input, 'books': books, 'algorithm_version': ALGORITHM}
        token = hashlib.sha256(canonical_json(raw).encode('utf-8')).hexdigest()
        return issues, None if issues else compare(goal_input, books), token

    def _saved(self, session, row):
        if row is None:
            return None
        try:
            snapshot = ComparisonSnapshot.model_validate_json(row.snapshot_json).model_dump()
            ids = [item['book_id'] for item in snapshot['books']]
            members = sorted(session.scalars(select(BookComparisonBook.book_id).where(
                BookComparisonBook.goal_id == row.goal_id)))
            if (len(set(ids)) != len(ids) or sorted(ids) != members or
                    [book['book_id'] for book in snapshot['preview']['books']] != members or
                    any(book['profile']['book_id'] != book['book_id']
                        for book in snapshot['preview']['books']) or
                    snapshot['preview']['goal']['book_ids'] != members or
                    snapshot['preview']['goal']['id'] != row.goal_id or
                    snapshot['revision'] != row.revision or snapshot['input_token'] != row.input_fingerprint or
                    snapshot['preview']['algorithm_version'] != row.algorithm_version or
                    snapshot['created_at'] != row.created_at or snapshot['updated_at'] != row.updated_at):
                raise ValueError('Inconsistent comparison snapshot')
            request = ComparisonRequest.model_validate({
                'input_token': row.input_fingerprint, 'expected_revision': row.revision,
                'books': [{key: value for key, value in book.items() if key != 'provenance'}
                          for book in snapshot['books']],
            })
            if self._judgments(request, snapshot['preview']) != snapshot['books']:
                raise ValueError('Inconsistent manual provenance')
            return snapshot
        except (ValidationError, ValueError, LibraryError) as exc:
            raise storage_error() from exc

    def _get(self, session, goal):
        issues, current, token = self._inputs(session, goal)
        row = session.get(BookComparison, goal.id)
        saved = self._saved(session, row)
        reasons = []
        if saved:
            if not goal.is_active:
                reasons.append('goal_inactive')
            if row.algorithm_version != ALGORITHM:
                reasons.append('algorithm_changed')
            if row.input_fingerprint != token:
                reasons.append('inputs_changed')
            if issues:
                reasons.append('inputs_not_ready')
        return {'goal_id': goal.id, 'is_active': goal.is_active,
                'readiness': {'ready': not issues, 'issues': issues},
                'input_token': token if not issues else None, 'current': current,
                'saved': saved, 'stale': bool(reasons), 'stale_reasons': reasons}

    @staticmethod
    def _goal(session, goal_id):
        goal = session.get(LearningGoal, goal_id)
        if goal is None:
            raise LibraryError(404, 'goal_not_found', 'Learning goal not found.')
        return goal

    def get(self, goal_id):
        with self.lock, Session(self.engine) as session:
            return self._get(session, self._goal(session, goal_id))

    @staticmethod
    def _judgments(body, preview):
        inputs = {book['book_id']: book for book in preview['books']}
        ids = [book.book_id for book in body.books]
        if len(set(ids)) != len(ids) or set(ids) != set(inputs):
            raise LibraryError(422, 'invalid_comparison_books',
                               'Classify each currently selected book exactly once.')
        result = []
        for book in sorted(body.books, key=lambda item: item.book_id):
            facts = inputs[book.book_id]
            if (len(set(book.focus_topics)) != len(book.focus_topics) or
                    not set(book.focus_topics) <= set(facts['topic_keys']) or
                    (book.role == 'selected_chapters' and not book.focus_topics)):
                raise LibraryError(422, 'invalid_focus_topics',
                                   'Choose valid unique focus topics; SELECTED CHAPTERS requires at least one.')
            refs = [ref.model_dump() for ref in book.evidence_refs]
            if len({canonical_json(ref) for ref in refs}) != len(refs):
                raise LibraryError(422, 'invalid_evidence', 'Evidence references must be unique.')
            for ref in refs:
                valid = False
                if ref['kind'] == 'profile_field':
                    valid = bool(facts['profile'][ref['field']])
                elif ref['kind'] == 'topic':
                    valid = ref['topic'] in facts['topic_keys']
                elif ref['kind'] == 'pair':
                    pair = next((pair for pair in preview['pairs'] if
                                 {pair['left_book_id'], pair['right_book_id']} ==
                                 {book.book_id, ref['other_book_id']}), None)
                    valid = pair is not None and pair[ref['dimension']] not in (None, 'unknown')
                if not valid:
                    raise LibraryError(422, 'invalid_evidence',
                                       'An evidence reference is missing or unknown in the current inputs.')
            value = book.model_dump()
            value['provenance'] = {field: 'manual' if value[field] else None
                                   for field in ('role', 'rationale', 'relevance', 'depth',
                                                 'practice', 'focus_topics', 'evidence_refs')}
            result.append(value)
        return result

    def put(self, goal_id, body):
        with self.lock:
            self.library.allow_mutation()
            with Session(self.engine) as session:
                goal = self._goal(session, goal_id)
                if not goal.is_active:
                    raise LibraryError(409, 'goal_inactive', 'Only the active goal can be changed.')
                envelope = self._get(session, goal)
                if not envelope['readiness']['ready']:
                    raise LibraryError(409, 'comparison_not_ready', 'Complete the required book profiles.',
                                       issues=envelope['readiness']['issues'])
                if envelope['input_token'] != body.input_token:
                    raise LibraryError(409, 'comparison_inputs_changed',
                                       'Comparison inputs changed. Review the current inputs before saving.')
                row = session.get(BookComparison, goal_id)
                if (row.revision if row else None) != body.expected_revision:
                    raise LibraryError(409, 'comparison_revision_conflict',
                                       'The saved comparison changed. Reload and review before saving.')
                judgments = self._judgments(body, envelope['current'])
                timestamp = utc_now()
                if row is None:
                    row = BookComparison(goal_id=goal_id, revision=1, created_at=timestamp)
                    session.add(row)
                else:
                    row.revision += 1
                row.updated_at = timestamp
                row.input_fingerprint = envelope['input_token']
                row.algorithm_version = ALGORITHM
                snapshot = ComparisonSnapshot.model_validate({
                    'preview': envelope['current'], 'books': judgments, 'revision': row.revision,
                    'input_token': row.input_fingerprint, 'created_at': row.created_at,
                    'updated_at': timestamp,
                }).model_dump()
                row.snapshot_json = canonical_json(snapshot)
                session.flush()
                session.execute(delete(BookComparisonBook).where(BookComparisonBook.goal_id == goal_id))
                session.add_all(BookComparisonBook(goal_id=goal_id, book_id=book['book_id'])
                                for book in judgments)
                session.commit()
                return self._get(session, goal)

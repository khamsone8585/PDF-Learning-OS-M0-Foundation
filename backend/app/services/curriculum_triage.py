"""Persisted large-library triage with atomic M3/M5 confirmation."""
import hashlib
import json
from collections import Counter
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.book_comparison import BookComparison, BookComparisonBook
from app.models.learning_goal import LearningGoal, LearningGoalBook
from app.models.library_intelligence import CurriculumTriage, CurriculumTriageBook
from app.schemas.book_comparison import ComparisonSnapshot
from app.services.book_comparisons import ALGORITHM as COMPARISON_ALGORITHM, BookComparisonService
from app.services.learning_goals import LearningGoalService, utc_now
from app.services.library_errors import LibraryError, storage_error
from app.services.library_intelligence import LibraryIntelligenceService
from app.services.profile_matching import canonical_json, keys, normalize

ALGORITHM = 'curriculum_triage_v1'
DIFFICULTY = {'beginner': 0, 'intermediate': 1, 'advanced': 2}


def canonical_triage_id(value):
    try:
        if str(UUID(value)) == value:
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    raise LibraryError(422, 'invalid_id', 'A canonical curriculum triage UUID is required.',
                       field='triage_id')


class CurriculumTriageService:
    def __init__(self, library):
        self.library = library
        self.engine = library.engine
        self.lock = library.lock
        self.intelligence = LibraryIntelligenceService(library)
        self.goals = LearningGoalService(library)
        self.comparisons = BookComparisonService(library)

    @staticmethod
    def _decode_topics(row):
        try:
            result = json.loads(row.target_topics_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise storage_error() from exc
        if not isinstance(result, list) or not all(isinstance(item, str) for item in result):
            raise storage_error()
        return result

    def _fields(self, body):
        title, description = self.goals._text(body.title, body.description)
        target_domain = body.target_domain.strip() if body.target_domain else None
        if target_domain == '':
            target_domain = None
        if target_domain is not None and len(target_domain) > 200:
            raise LibraryError(422, 'invalid_target_domain',
                               'Target domain must contain at most 200 characters.')
        topics, seen = [], set()
        for topic in body.target_topics:
            topic = topic.strip()
            key = normalize(topic)
            if not topic or len(topic) > 200:
                raise LibraryError(422, 'invalid_target_topics',
                                   'Each target topic must contain 1–200 characters.')
            if key in seen:
                raise LibraryError(422, 'duplicate_target_topics',
                                   'Target topics must be distinct after exact normalization.')
            seen.add(key)
            topics.append(topic)
        return title, description, target_domain, topics

    @staticmethod
    def _canonical_ids(session, values):
        result = []
        for value in values:
            try:
                canonical = str(UUID(value))
            except (TypeError, ValueError, AttributeError) as exc:
                raise LibraryError(422, 'invalid_book_id',
                                   'Every candidate book ID must be a canonical UUID.') from exc
            if canonical != value:
                raise LibraryError(422, 'invalid_book_id',
                                   'Every candidate book ID must be a canonical UUID.')
            result.append(value)
        if len(result) != len(set(result)):
            raise LibraryError(422, 'duplicate_book_ids', 'Choose each candidate book only once.')
        existing = set(session.scalars(select(Book.id).where(Book.id.in_(result)))) if result else set()
        missing = sorted(set(result) - existing)
        if missing:
            raise LibraryError(404, 'books_not_found', 'One or more candidate books were not found.',
                               missing_book_ids=missing)
        return sorted(result)

    def _scope(self, session, scope):
        if scope.kind == 'library_snapshot':
            if scope.book_ids:
                raise LibraryError(422, 'invalid_triage_scope',
                                   'Library snapshot scope captures the current library automatically.')
            return sorted(session.scalars(select(Book.id)))
        return self._canonical_ids(session, scope.book_ids)

    @staticmethod
    def _fingerprint_ids(ids):
        return hashlib.sha256(canonical_json(sorted(ids)).encode()).hexdigest()

    @staticmethod
    def _candidate_ids(session, triage_id):
        return list(session.scalars(select(CurriculumTriageBook.book_id).where(
            CurriculumTriageBook.triage_id == triage_id).order_by(CurriculumTriageBook.book_id)))

    def _view(self, session, row):
        return {
            'id': row.id, 'title': row.title, 'description': row.description,
            'target_topics': self._decode_topics(row), 'target_domain': row.target_domain,
            'difficulty_ceiling': row.difficulty_ceiling, 'scope_kind': row.scope_kind,
            'book_ids': self._candidate_ids(session, row.id), 'revision': row.revision,
            'algorithm_version': row.algorithm_version, 'status': row.status,
            'applied_goal_id': row.applied_goal_id, 'created_at': row.created_at,
            'updated_at': row.updated_at, 'applied_at': row.applied_at,
        }

    def _token(self, session, row, rows, reviews):
        raw = {
            'triage': {
                'id': row.id, 'title': row.title, 'description': row.description,
                'target_topics': self._decode_topics(row), 'target_domain': row.target_domain,
                'difficulty_ceiling': row.difficulty_ceiling, 'scope_kind': row.scope_kind,
                'book_ids': sorted(item['book_id'] for item in rows),
            },
            'books': [{key: item[key] for key in ('book_id', 'title', 'author', 'edition', 'year',
                                                   'profile', 'topic_keys', 'prerequisite_keys',
                                                   'domain_key')}
                      for item in sorted(rows, key=lambda item: item['book_id'])],
            'reviews': [{'left_book_id': pair[0], 'right_book_id': pair[1], **review}
                        for pair, review in sorted(reviews.items())],
            'algorithm_version': ALGORITHM,
        }
        return hashlib.sha256(canonical_json(raw).encode()).hexdigest()

    @staticmethod
    def _recommend(row, rows, bibliographic, overlaps, reviews, target_topics):
        target = set(keys(target_topics))
        domain = normalize(row.target_domain) if row.target_domain else None
        ceiling = DIFFICULTY.get(row.difficulty_ceiling) if row.difficulty_ceiling else None
        topic_counts = Counter(topic for item in rows for topic in item['topic_keys'])
        direct_ids = {item['book_id'] for item in rows if target & set(item['topic_keys'])}
        needed_prerequisites = set()
        for item in rows:
            if item['book_id'] in direct_ids:
                needed_prerequisites.update(item['prerequisite_keys'])

        same_work_preference = {}
        for pair, review in reviews.items():
            if review['decision'] == 'same_work':
                other = pair[1] if review['preferred_book_id'] == pair[0] else pair[0]
                same_work_preference[other] = review['preferred_book_id']
        probable_pairs = {frozenset((item['left_book_id'], item['right_book_id']))
                          for item in bibliographic if item['classification'] == 'probable_duplicate'
                          and item['review'] is None}
        high_overlap = {frozenset((item['left_book_id'], item['right_book_id']))
                        for item in overlaps if item['classification'] in
                        ('recorded_topic_equivalent', 'recorded_topic_subset')}

        facts = []
        for item in rows:
            topics = set(item['topic_keys'])
            direct = sorted(target & topics)
            foundation = sorted(needed_prerequisites & (topics | ({item['domain_key']} if item['domain_key'] else set())))
            unique = sorted(topic for topic in topics if topic_counts[topic] == 1)
            supporting = bool(domain and item['domain_key'] == domain and unique)
            if item['readiness'] != 'triage_ready':
                band = 'insufficient_data'
            elif direct:
                band = 'direct'
            elif foundation:
                band = 'foundation'
            elif supporting:
                band = 'supporting'
            else:
                band = 'no_recorded_match'
            difficulty = item['profile']['difficulty'] if item['profile'] else None
            above = ceiling is not None and difficulty is not None and DIFFICULTY[difficulty] > ceiling
            facts.append({
                'book_id': item['book_id'], 'title': item['title'], 'band': band,
                'matched_target_topics': direct, 'matched_prerequisites': foundation,
                'unique_topics': unique, 'difficulty': difficulty,
                'orientation': item['profile']['orientation'] if item['profile'] else None,
                'above_ceiling': above, 'preferred_same_work_book_id': same_work_preference.get(item['book_id']),
                'source': 'derived', 'algorithm_version': ALGORITHM,
            })

        by_id = {item['book_id']: item for item in facts}
        eligible = [item for item in facts if item['band'] in ('direct', 'foundation', 'supporting')
                    and not item['above_ceiling'] and not item['preferred_same_work_book_id']]
        selected, covered_targets, covered_prerequisites, orientations = [], set(), set(), set()

        def conflicts(candidate):
            pair_sets = [frozenset((candidate['book_id'], chosen['book_id'])) for chosen in selected]
            return any(pair in probable_pairs for pair in pair_sets), any(pair in high_overlap for pair in pair_sets)

        def rank(candidate, phase):
            new_targets = len(set(candidate['matched_target_topics']) - covered_targets)
            new_prereqs = len(set(candidate['matched_prerequisites']) - covered_prerequisites)
            _duplicate, redundant = conflicts(candidate)
            orientation_new = int(bool(candidate['orientation'] and candidate['orientation'] not in orientations))
            known_difficulty = int(candidate['difficulty'] is not None)
            band_rank = {'direct': 0, 'foundation': 1, 'supporting': 2}[candidate['band']]
            if phase == 'foundation':
                band_rank = 0 if candidate['band'] == 'foundation' else 1
            return (band_rank, -new_targets, -new_prereqs, redundant,
                    -len(candidate['unique_topics']), -known_difficulty, -orientation_new,
                    normalize(candidate['title']), candidate['book_id'])

        def add(candidate):
            selected.append(candidate)
            covered_targets.update(candidate['matched_target_topics'])
            covered_prerequisites.update(candidate['matched_prerequisites'])
            if candidate['orientation']:
                orientations.add(candidate['orientation'])

        remaining = eligible[:]
        while remaining and len(selected) < 3 and covered_targets != target:
            direct = [item for item in remaining if item['band'] == 'direct' and not conflicts(item)[0]]
            if not direct:
                break
            choice = min(direct, key=lambda item: rank(item, 'direct'))
            add(choice); remaining.remove(choice)
        selected_direct_ids = {item['book_id'] for item in selected if item['band'] == 'direct'}
        selected_prerequisites = set()
        for item in rows:
            if item['book_id'] in selected_direct_ids:
                selected_prerequisites.update(item['prerequisite_keys'])
        while remaining and len(selected) < 5 and selected_prerequisites - covered_prerequisites:
            needed = selected_prerequisites - covered_prerequisites
            foundations = [item for item in remaining
                           if needed & set(item['matched_prerequisites']) and not conflicts(item)[0]]
            if not foundations:
                break
            choice = min(foundations, key=lambda item: rank(item, 'foundation'))
            add(choice); remaining.remove(choice)
        while remaining and len(selected) < 3:
            choices = [item for item in remaining if not conflicts(item)[0]]
            if not choices:
                break
            choice = min(choices, key=lambda item: rank(item, 'fill'))
            add(choice); remaining.remove(choice)
        while remaining and len(selected) < 5:
            useful = [item for item in remaining if
                      not conflicts(item)[0] and (
                          set(item['matched_target_topics']) - covered_targets or
                          set(item['matched_prerequisites']) - covered_prerequisites or
                          (item['orientation'] and item['orientation'] not in orientations))]
            if not useful:
                break
            choice = min(useful, key=lambda item: rank(item, 'extend'))
            add(choice); remaining.remove(choice)

        ids = [item['book_id'] for item in selected]
        issues = []
        if len(ids) < 3:
            issues.append({'code': 'insufficient_recommendation_evidence',
                           'message': 'Fewer than three candidates have exact supporting evidence.'})
        if target - covered_targets:
            issues.append({'code': 'target_topics_uncovered',
                           'topics': sorted(target - covered_targets),
                           'message': 'Some target topics are not covered by the shortlist.'})
        unreviewed = sorted([sorted(pair) for pair in probable_pairs
                             if pair & set(ids)], key=lambda pair: tuple(pair))
        if unreviewed:
            issues.append({'code': 'probable_duplicates_unreviewed', 'pairs': unreviewed,
                           'message': 'Review probable duplicate candidates before removing any book.'})
        return {'suggested_book_ids': ids, 'partial': len(ids) < 3, 'issues': issues,
                'covered_target_topics': sorted(covered_targets),
                'uncovered_target_topics': sorted(target - covered_targets),
                'books': [by_id[item['book_id']] for item in sorted(facts, key=lambda item: item['book_id'])],
                'algorithm_version': ALGORITHM, 'ordering_has_study_sequence_meaning': False}

    def _envelope(self, session, row):
        candidate_ids = self._candidate_ids(session, row.id)
        rows, bibliographic, overlaps, prerequisites, reviews = self.intelligence.facts(session, set(candidate_ids))
        token = self._token(session, row, rows, reviews)
        current_scope = self._fingerprint_ids(candidate_ids)
        stale_reasons = []
        if current_scope != row.scope_fingerprint:
            stale_reasons.append('candidate_deleted')
        if row.scope_kind == 'library_snapshot':
            library_ids = list(session.scalars(select(Book.id).order_by(Book.id)))
            if self._fingerprint_ids(library_ids) != row.scope_fingerprint:
                stale_reasons.append('library_membership_changed')
        if row.algorithm_version != ALGORITHM:
            stale_reasons.append('algorithm_changed')
        if token != row.input_fingerprint:
            stale_reasons.append('inputs_changed')
        issues = []
        for item in rows:
            if item['readiness'] != 'triage_ready':
                issues.append({'code': item['readiness'], 'book_id': item['book_id'],
                               'message': 'Record a profile and at least one main topic.'})
        recommendation = self._recommend(row, rows, bibliographic, overlaps, reviews,
                                         self._decode_topics(row))
        candidates = [{**item, 'profile': item['profile']} for item in rows]
        return {'session': self._view(session, row), 'candidates': candidates,
                'readiness': {'ready_count': sum(item['readiness'] == 'triage_ready' for item in rows),
                              'candidate_count': len(rows), 'issues': issues,
                              'prerequisite_count': len(prerequisites)},
                'recommendation': recommendation, 'input_token': token,
                'stale': bool(stale_reasons), 'stale_reasons': list(dict.fromkeys(stale_reasons))}

    @staticmethod
    def _row(session, triage_id):
        row = session.get(CurriculumTriage, triage_id)
        if row is None:
            raise LibraryError(404, 'triage_not_found', 'Curriculum triage not found.')
        return row

    def create(self, body):
        title, description, domain, topics = self._fields(body)
        with self.lock:
            self.library.allow_mutation()
            with Session(self.engine) as session:
                draft = session.scalar(select(CurriculumTriage).where(CurriculumTriage.status == 'draft'))
                if draft:
                    if not body.archive_draft_id or canonical_triage_id(body.archive_draft_id) != draft.id:
                        raise LibraryError(409, 'triage_draft_exists',
                                           'Archive the existing draft explicitly before starting another.')
                    draft.status = 'archived'
                    draft.updated_at = utc_now()
                    session.flush()
                ids = self._scope(session, body.scope)
                timestamp, triage_id = utc_now(), str(uuid4())
                row = CurriculumTriage(
                    id=triage_id, title=title, description=description, target_domain=domain,
                    target_topics_json=json.dumps(topics, ensure_ascii=False, separators=(',', ':')),
                    difficulty_ceiling=body.difficulty_ceiling, scope_kind=body.scope.kind,
                    revision=1, scope_fingerprint=self._fingerprint_ids(ids),
                    input_fingerprint='0' * 64, algorithm_version=ALGORITHM, status='draft',
                    created_at=timestamp, updated_at=timestamp, applied_at=None,
                )
                session.add(row)
                session.add_all(CurriculumTriageBook(triage_id=triage_id, book_id=book_id)
                                for book_id in ids)
                session.flush()
                envelope = self._envelope(session, row)
                row.input_fingerprint = envelope['input_token']
                session.commit()
                return self._envelope(session, row)

    def list(self):
        with self.lock, Session(self.engine) as session:
            rows = list(session.scalars(select(CurriculumTriage).order_by(
                CurriculumTriage.created_at.desc(), CurriculumTriage.id)))
            return {'triages': [self._view(session, row) for row in rows]}

    def get(self, triage_id):
        with self.lock, Session(self.engine) as session:
            return self._envelope(session, self._row(session, triage_id))

    def update(self, triage_id, body):
        title, description, domain, topics = self._fields(body)
        with self.lock:
            self.library.allow_mutation()
            with Session(self.engine) as session:
                row = self._row(session, triage_id)
                if row.status != 'draft':
                    raise LibraryError(409, 'triage_not_editable', 'Only a draft triage can be changed.')
                current = self._envelope(session, row)
                if row.revision != body.expected_revision:
                    raise LibraryError(409, 'triage_revision_conflict',
                                       'The triage changed. Reload before saving.')
                if current['input_token'] != body.input_token:
                    raise LibraryError(409, 'triage_inputs_changed',
                                       'Library inputs changed. Reload and review before saving.')
                ids = self._scope(session, body.scope)
                row.title, row.description, row.target_domain = title, description, domain
                row.target_topics_json = json.dumps(topics, ensure_ascii=False, separators=(',', ':'))
                row.difficulty_ceiling, row.scope_kind = body.difficulty_ceiling, body.scope.kind
                row.scope_fingerprint = self._fingerprint_ids(ids)
                row.algorithm_version = ALGORITHM
                row.revision += 1
                row.updated_at = utc_now()
                session.execute(delete(CurriculumTriageBook).where(
                    CurriculumTriageBook.triage_id == triage_id))
                session.add_all(CurriculumTriageBook(triage_id=triage_id, book_id=book_id)
                                for book_id in ids)
                session.flush()
                row.input_fingerprint = self._envelope(session, row)['input_token']
                session.commit()
                return self._envelope(session, row)

    def confirm(self, triage_id, body):
        with self.lock:
            self.library.allow_mutation()
            with Session(self.engine) as session:
                row = self._row(session, triage_id)
                if row.status != 'draft':
                    raise LibraryError(409, 'triage_not_editable', 'Only a draft triage can be confirmed.')
                current = self._envelope(session, row)
                if row.revision != body.expected_revision:
                    raise LibraryError(409, 'triage_revision_conflict',
                                       'The triage changed. Reload before confirming.')
                if current['stale'] or current['input_token'] != body.input_token:
                    raise LibraryError(409, 'triage_inputs_changed',
                                       'Library inputs changed. Synchronize and review before confirming.')
                ids = [item.book_id for item in body.books]
                if len(ids) != len(set(ids)):
                    raise LibraryError(422, 'invalid_comparison_books',
                                       'Choose each confirmed book exactly once.')
                candidates = set(self._candidate_ids(session, row.id))
                if not set(ids) <= candidates:
                    raise LibraryError(422, 'invalid_triage_books',
                                       'Every confirmed book must belong to the triage scope.')
                if any(item.role == 'skip_for_now' for item in body.books):
                    raise LibraryError(422, 'later_not_study_now',
                                       'LATER books cannot be included in Books Now.')
                if not any(item.role in ('core', 'selected_chapters') for item in body.books):
                    raise LibraryError(422, 'primary_book_required',
                                       'Books Now requires at least one CORE or SELECTED book.')
                selected = self.goals._books(session, ids)
                timestamp = utc_now()
                previous = session.scalar(select(LearningGoal).where(LearningGoal.is_active.is_(True)))
                if previous:
                    previous.is_active = False
                    previous.updated_at = timestamp
                    session.flush()
                goal = LearningGoal(id=str(uuid4()), title=row.title, description=row.description,
                                    is_active=True, created_at=timestamp, updated_at=timestamp)
                session.add(goal)
                session.add_all(LearningGoalBook(goal_id=goal.id, book_id=book_id)
                                for book_id in selected)
                session.flush()
                issues, preview, token = self.comparisons._inputs(session, goal)
                if issues or preview is None:
                    raise LibraryError(409, 'comparison_not_ready',
                                       'Every confirmed book needs a profile and main topic.', issues=issues)
                judgments = self.comparisons._judgments(body, preview)
                comparison = BookComparison(
                    goal_id=goal.id, revision=1, input_fingerprint=token,
                    algorithm_version=COMPARISON_ALGORITHM, created_at=timestamp, updated_at=timestamp,
                    snapshot_json='{}',
                )
                session.add(comparison)
                snapshot = ComparisonSnapshot.model_validate({
                    'preview': preview, 'books': judgments, 'revision': 1,
                    'input_token': token, 'created_at': timestamp, 'updated_at': timestamp,
                }).model_dump()
                comparison.snapshot_json = canonical_json(snapshot)
                session.add_all(BookComparisonBook(goal_id=goal.id, book_id=book_id)
                                for book_id in selected)
                row.status = 'applied'
                row.applied_goal_id = goal.id
                row.applied_at = timestamp
                row.updated_at = timestamp
                row.revision += 1
                session.commit()
                return {'triage': self._view(session, row),
                        'goal': self.goals._view(session, goal),
                        'comparison': self.comparisons._get(session, goal)}

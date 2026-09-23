"""Deterministic library-scale facts derived only from metadata and M4 profiles."""
import hashlib
from collections import Counter, defaultdict
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.book_profile import BookProfile
from app.models.library_intelligence import LibraryRelationReview
from app.schemas.book_profile import BookProfileResponse
from app.services.book_profiles import BookProfileService
from app.services.learning_goals import utc_now
from app.services.library_errors import LibraryError, storage_error
from app.services.library_storage import canonical_id
from app.services.profile_matching import canonical_json, keys, normalize

MATCHING_ALGORITHM = 'profile_exact_v1'
BIBLIOGRAPHIC_ALGORITHM = 'bibliographic_exact_v1'


class LibraryIntelligenceService:
    def __init__(self, library):
        self.library = library
        self.engine = library.engine
        self.lock = library.lock
        self.profiles = BookProfileService(library)

    def _rows(self, session, candidate_ids=None):
        query = select(Book).order_by(Book.title, Book.id)
        if candidate_ids is not None:
            query = query.where(Book.id.in_(candidate_ids))
        books = list(session.scalars(query))
        profiles = {profile.book_id: profile for profile in session.scalars(select(BookProfile).where(
            BookProfile.book_id.in_([book.id for book in books]))) } if books else {}
        rows = []
        for book in books:
            profile = profiles.get(book.id)
            try:
                view = (BookProfileResponse.model_validate(self.profiles._view(profile)).model_dump()
                        if profile else None)
            except (ValueError, TypeError) as exc:
                raise storage_error() from exc
            topics = keys(view['main_topics']) if view else []
            prerequisites = keys(view['prerequisites']) if view else []
            domain_key = normalize(view['domain']) if view and view['domain'] else None
            readiness = 'profile_missing' if view is None else 'topics_missing' if not topics else 'triage_ready'
            rows.append({
                'book_id': book.id, 'title': book.title, 'author': book.author,
                'edition': book.edition, 'year': book.year, 'processing_status': book.processing_status,
                'toc_status': book.toc_status, 'profile': view, 'readiness': readiness,
                'domain_key': domain_key, 'topic_keys': topics, 'prerequisite_keys': prerequisites,
            })
        return rows

    @staticmethod
    def _reviews(session, ids=None):
        query = select(LibraryRelationReview)
        if ids is not None:
            query = query.where(LibraryRelationReview.left_book_id.in_(ids),
                                LibraryRelationReview.right_book_id.in_(ids))
        return {(row.left_book_id, row.right_book_id): {
            'decision': row.decision, 'preferred_book_id': row.preferred_book_id,
            'note': row.note, 'source': 'manual', 'updated_at': row.updated_at,
        } for row in session.scalars(query)}

    @staticmethod
    def _bibliographic(rows):
        groups = defaultdict(list)
        for row in rows:
            if row['author']:
                groups[(normalize(row['title']), normalize(row['author']))].append(row)
        result = []
        for group in groups.values():
            for first, second in combinations(group, 2):
                left, right = sorted((first, second), key=lambda item: item['book_id'])
                edition_conflict = (left['edition'] and right['edition'] and
                                    normalize(left['edition']) != normalize(right['edition']))
                year_conflict = (left['year'] is not None and right['year'] is not None and
                                 left['year'] != right['year'])
                result.append({
                    'left_book_id': left['book_id'], 'right_book_id': right['book_id'],
                    'classification': ('related_edition' if edition_conflict or year_conflict
                                       else 'probable_duplicate'),
                    'algorithm_version': BIBLIOGRAPHIC_ALGORITHM,
                    'evidence': ['normalized_title', 'normalized_author'] +
                                (['edition_conflict'] if edition_conflict else []) +
                                (['year_conflict'] if year_conflict else []),
                })
        return result

    @staticmethod
    def _overlaps(rows):
        result = []
        counts = Counter(topic for row in rows for topic in row['topic_keys'])
        inverted = defaultdict(list)
        for row in rows:
            row['unique_topics'] = sorted(topic for topic in row['topic_keys'] if counts[topic] == 1)
            for topic in row['topic_keys']:
                inverted[topic].append(row['book_id'])
        candidate_pairs = set()
        for book_ids in inverted.values():
            candidate_pairs.update(combinations(sorted(set(book_ids)), 2))
        by_id = {row['book_id']: row for row in rows}
        for left_id, right_id in sorted(candidate_pairs):
            left, right = by_id[left_id], by_id[right_id]
            left_topics, right_topics = set(left['topic_keys']), set(right['topic_keys'])
            shared = sorted(left_topics & right_topics)
            left_only, right_only = sorted(left_topics - right_topics), sorted(right_topics - left_topics)
            if len(shared) >= 2 and left_topics == right_topics:
                classification = 'recorded_topic_equivalent'
            elif len(shared) >= 2 and (left_topics <= right_topics or right_topics <= left_topics):
                classification = 'recorded_topic_subset'
            else:
                classification = 'recorded_topic_overlap'
            result.append({
                'left_book_id': left['book_id'], 'right_book_id': right['book_id'],
                'classification': classification, 'shared_topics': shared,
                'left_only': left_only, 'right_only': right_only,
                'complementary': bool(left_only and right_only),
                'algorithm_version': MATCHING_ALGORITHM, 'source': 'derived',
            })
        return result

    @staticmethod
    def _prerequisites(rows):
        providers = defaultdict(list)
        for row in rows:
            for topic in row['topic_keys']:
                providers[topic].append((row['book_id'], 'main_topics'))
            if row['domain_key']:
                providers[row['domain_key']].append((row['book_id'], 'domain'))
        result = []
        for row in rows:
            profile = row['profile']
            if profile is None:
                continue
            for original in profile['prerequisites']:
                key = normalize(original)
                matches = [{'book_id': book_id, 'field': field, 'source': 'derived'}
                           for book_id, field in sorted(set(providers.get(key, [])))
                           if book_id != row['book_id']]
                result.append({
                    'book_id': row['book_id'], 'prerequisite': original, 'normalized_key': key,
                    'profile_source': profile['provenance']['prerequisites'],
                    'providers': matches, 'unresolved': not matches,
                    'algorithm_version': MATCHING_ALGORITHM,
                })
        return result

    def facts(self, session, candidate_ids=None):
        rows = self._rows(session, candidate_ids)
        ids = {row['book_id'] for row in rows}
        reviews = self._reviews(session, ids)
        bibliographic = self._bibliographic(rows)
        for item in bibliographic:
            item['review'] = reviews.get((item['left_book_id'], item['right_book_id']))
        overlaps = self._overlaps(rows)
        prerequisites = self._prerequisites(rows)
        return rows, bibliographic, overlaps, prerequisites, reviews

    def map(self):
        with self.lock, Session(self.engine) as session:
            rows, bibliographic, overlaps, prerequisites, _reviews = self.facts(session)
            bibliographic_counts, overlap_counts = Counter(), Counter()
            for item in bibliographic:
                bibliographic_counts[item['left_book_id']] += 1
                bibliographic_counts[item['right_book_id']] += 1
            for item in overlaps:
                overlap_counts[item['left_book_id']] += 1
                overlap_counts[item['right_book_id']] += 1
            prerequisite_counts = Counter(item['book_id'] for item in prerequisites)
            books = []
            for row in rows:
                book_id = row['book_id']
                books.append({
                    **row,
                    'bibliographic_relation_count': bibliographic_counts[book_id],
                    'topic_relation_count': overlap_counts[book_id],
                    'unique_topic_count': len(row['unique_topics']),
                    'prerequisite_count': prerequisite_counts[book_id],
                })
            domain_counts = Counter(row['domain_key'] or 'unknown' for row in rows)
            topic_counts = Counter(topic for row in rows for topic in row['topic_keys'])
            readiness_counts = Counter(row['readiness'] for row in rows)
            raw = [{key: row[key] for key in ('book_id', 'title', 'author', 'edition', 'year',
                                               'processing_status', 'toc_status', 'profile')}
                   for row in sorted(rows, key=lambda item: item['book_id'])]
            return {
                'library_token': hashlib.sha256(canonical_json(raw).encode()).hexdigest(),
                'exact_content_duplicates_prevented': True,
                'counts': {'books': len(rows), **{key: readiness_counts[key] for key in
                           ('profile_missing', 'topics_missing', 'triage_ready')},
                           'bibliographic_relations': len(bibliographic),
                           'topic_relations': len(overlaps),
                           'unresolved_prerequisites': sum(item['unresolved'] for item in prerequisites)},
                'groups': {
                    'domains': [{'key': key, 'label': key if key != 'unknown' else 'Unknown', 'count': count}
                                for key, count in sorted(domain_counts.items())],
                    'topics': [{'key': key, 'label': key, 'count': count}
                               for key, count in sorted(topic_counts.items())],
                    'readiness': [{'key': key, 'label': key.replace('_', ' ').title(), 'count': count}
                                  for key, count in sorted(readiness_counts.items())],
                },
                'books': books,
            }

    def relations(self, kind, offset, limit, book_id=None):
        if book_id is not None:
            book_id = canonical_id(book_id)
        with self.lock, Session(self.engine) as session:
            _rows, bibliographic, overlaps, _prerequisites, _reviews = self.facts(session)
            items = bibliographic if kind == 'bibliographic' else overlaps
            if book_id:
                items = [item for item in items if book_id in (item['left_book_id'], item['right_book_id'])]
            items.sort(key=lambda item: (item['classification'], item['left_book_id'], item['right_book_id']))
            return {'kind': kind, 'total': len(items), 'offset': offset, 'limit': limit,
                    'items': items[offset:offset + limit]}

    def prerequisites(self, offset, limit, book_id=None):
        if book_id is not None:
            book_id = canonical_id(book_id)
        with self.lock, Session(self.engine) as session:
            _rows, _bibliographic, _overlaps, items, _reviews = self.facts(session)
            if book_id:
                items = [item for item in items if item['book_id'] == book_id]
            items.sort(key=lambda item: (item['book_id'], item['normalized_key']))
            return {'total': len(items), 'offset': offset, 'limit': limit,
                    'items': items[offset:offset + limit]}

    def review(self, body):
        left, right = sorted((canonical_id(body.left_book_id), canonical_id(body.right_book_id)))
        if left == right:
            raise LibraryError(422, 'invalid_relation_pair', 'Choose two different books.')
        preferred = canonical_id(body.preferred_book_id) if body.preferred_book_id else None
        if body.decision == 'same_work' and preferred not in (left, right):
            raise LibraryError(422, 'invalid_preferred_book', 'Choose one book in the pair to retain.')
        if body.decision != 'same_work' and preferred is not None:
            raise LibraryError(422, 'invalid_preferred_book', 'Only same-work reviews have a preferred book.')
        note = body.note.strip() if body.note else None
        if note == '':
            note = None
        with self.lock:
            self.library.allow_mutation()
            with Session(self.engine) as session:
                books = set(session.scalars(select(Book.id).where(Book.id.in_((left, right)))))
                if books != {left, right}:
                    raise LibraryError(404, 'books_not_found', 'One or more reviewed books were not found.')
                rows = self._rows(session, {left, right})
                if not self._bibliographic(rows):
                    raise LibraryError(409, 'relation_not_candidate',
                                       'This pair is not a deterministic bibliographic candidate.')
                timestamp = utc_now()
                review = session.get(LibraryRelationReview, (left, right))
                if review is None:
                    review = LibraryRelationReview(left_book_id=left, right_book_id=right,
                                                   created_at=timestamp, updated_at=timestamp)
                    session.add(review)
                review.decision = body.decision
                review.preferred_book_id = preferred
                review.note = note
                review.updated_at = timestamp
                session.commit()
                return {'left_book_id': left, 'right_book_id': right,
                        'decision': review.decision, 'preferred_book_id': review.preferred_book_id,
                        'note': review.note, 'source': 'manual', 'created_at': review.created_at,
                        'updated_at': review.updated_at}

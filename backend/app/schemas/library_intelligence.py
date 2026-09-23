from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.book_comparison import ComparisonEnvelope, Judgment, Token
from app.schemas.book_profile import BookProfileResponse, Difficulty, Orientation, Source
from app.schemas.learning_goal import LearningGoalResponse


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class RelationReviewRequest(StrictModel):
    left_book_id: str
    right_book_id: str
    decision: Literal['same_work', 'related_edition', 'distinct']
    preferred_book_id: str | None = None
    note: str | None = Field(default=None, max_length=1000)


class RelationReviewSummary(StrictModel):
    decision: Literal['same_work', 'related_edition', 'distinct']
    preferred_book_id: str | None
    note: str | None
    source: Literal['manual']
    updated_at: str


class RelationReviewResponse(RelationReviewSummary):
    left_book_id: str
    right_book_id: str
    created_at: str


class TriageScope(StrictModel):
    kind: Literal['library_snapshot', 'selected']
    book_ids: list[str] = Field(default_factory=list, max_length=1000)


class TriageFields(StrictModel):
    title: str
    description: str | None = None
    target_topics: list[str] = Field(min_length=1, max_length=25)
    target_domain: str | None = None
    difficulty_ceiling: Difficulty | None = None
    scope: TriageScope


class TriageCreate(TriageFields):
    archive_draft_id: str | None = None


class TriageUpdate(TriageFields):
    input_token: Token
    expected_revision: int = Field(ge=1, strict=True)


class TriageConfirm(StrictModel):
    input_token: Token
    expected_revision: int = Field(ge=1, strict=True)
    reviewed_recommendation: Literal[True]
    books: list[Judgment] = Field(min_length=3, max_length=5)


class GroupCount(StrictModel):
    key: str
    label: str
    count: int = Field(ge=0)


class LibraryGroups(StrictModel):
    domains: list[GroupCount]
    topics: list[GroupCount]
    readiness: list[GroupCount]


class LibraryCounts(StrictModel):
    books: int = Field(ge=0)
    profile_missing: int = Field(ge=0)
    topics_missing: int = Field(ge=0)
    triage_ready: int = Field(ge=0)
    bibliographic_relations: int = Field(ge=0)
    topic_relations: int = Field(ge=0)
    unresolved_prerequisites: int = Field(ge=0)


class CandidateBook(StrictModel):
    book_id: str
    title: str
    author: str | None
    edition: str | None
    year: int | None
    processing_status: Literal['unprocessed', 'processing', 'processed', 'failed']
    toc_status: Literal['available', 'partial', 'missing', 'invalid'] | None
    profile: BookProfileResponse | None
    readiness: Literal['profile_missing', 'topics_missing', 'triage_ready']
    domain_key: str | None
    topic_keys: list[str]
    prerequisite_keys: list[str]
    unique_topics: list[str]


class MapBook(CandidateBook):
    bibliographic_relation_count: int = Field(ge=0)
    topic_relation_count: int = Field(ge=0)
    unique_topic_count: int = Field(ge=0)
    prerequisite_count: int = Field(ge=0)


class LibraryMapResponse(StrictModel):
    library_token: Token
    exact_content_duplicates_prevented: Literal[True]
    counts: LibraryCounts
    groups: LibraryGroups
    books: list[MapBook]


class Relation(StrictModel):
    left_book_id: str
    right_book_id: str
    classification: Literal['probable_duplicate', 'related_edition', 'recorded_topic_equivalent',
                            'recorded_topic_subset', 'recorded_topic_overlap']
    algorithm_version: str
    evidence: list[str] | None = None
    shared_topics: list[str] | None = None
    left_only: list[str] | None = None
    right_only: list[str] | None = None
    complementary: bool | None = None
    source: Literal['derived'] | None = None
    review: RelationReviewSummary | None = None


class RelationPage(StrictModel):
    kind: Literal['bibliographic', 'topic_overlap']
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[Relation]


class PrerequisiteProvider(StrictModel):
    book_id: str
    field: Literal['main_topics', 'domain']
    source: Literal['derived']


class Prerequisite(StrictModel):
    book_id: str
    prerequisite: str
    normalized_key: str
    profile_source: Source
    providers: list[PrerequisiteProvider]
    unresolved: bool
    algorithm_version: str


class PrerequisitePage(StrictModel):
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[Prerequisite]


class TriageSession(StrictModel):
    id: str
    title: str
    description: str | None
    target_topics: list[str]
    target_domain: str | None
    difficulty_ceiling: Difficulty | None
    scope_kind: Literal['library_snapshot', 'selected']
    book_ids: list[str]
    revision: int = Field(ge=1)
    algorithm_version: str
    status: Literal['draft', 'applied', 'archived', 'invalidated']
    applied_goal_id: str | None
    created_at: str
    updated_at: str
    applied_at: str | None


class TriageReadinessIssue(StrictModel):
    code: Literal['profile_missing', 'topics_missing']
    book_id: str
    message: str


class TriageReadiness(StrictModel):
    ready_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    issues: list[TriageReadinessIssue]
    prerequisite_count: int = Field(ge=0)


class RecommendationIssue(StrictModel):
    code: Literal['insufficient_recommendation_evidence', 'target_topics_uncovered',
                  'probable_duplicates_unreviewed']
    message: str
    topics: list[str] | None = None
    pairs: list[list[str]] | None = None


class RecommendationBook(StrictModel):
    book_id: str
    title: str
    band: Literal['direct', 'foundation', 'supporting', 'no_recorded_match',
                  'insufficient_data']
    matched_target_topics: list[str]
    matched_prerequisites: list[str]
    unique_topics: list[str]
    difficulty: Difficulty | None
    orientation: Orientation | None
    above_ceiling: bool
    preferred_same_work_book_id: str | None
    source: Literal['derived']
    algorithm_version: str


class Recommendation(StrictModel):
    suggested_book_ids: list[str] = Field(max_length=5)
    partial: bool
    issues: list[RecommendationIssue]
    covered_target_topics: list[str]
    uncovered_target_topics: list[str]
    books: list[RecommendationBook]
    algorithm_version: str
    ordering_has_study_sequence_meaning: Literal[False]


class TriageEnvelope(StrictModel):
    session: TriageSession
    candidates: list[CandidateBook]
    readiness: TriageReadiness
    recommendation: Recommendation
    input_token: Token
    stale: bool
    stale_reasons: list[str]


class TriageList(StrictModel):
    triages: list[TriageSession]


class TriageConfirmation(StrictModel):
    triage: TriageSession
    goal: LearningGoalResponse
    comparison: ComparisonEnvelope

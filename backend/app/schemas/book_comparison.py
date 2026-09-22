from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.book_profile import BookProfileResponse

Text1000 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Rationale = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Token = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{64}$')]
ProfileField = Literal['domain', 'difficulty', 'prerequisites', 'main_topics', 'orientation',
                       'strengths', 'weaknesses', 'suggested_use']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Relevance(StrictModel):
    category: Literal['high', 'partial', 'low', 'unknown']
    explanation: Text1000


class Depth(StrictModel):
    category: Literal['overview', 'working_detail', 'deep_treatment']
    explanation: Text1000


class Practice(StrictModel):
    category: Literal['limited', 'some', 'substantial']
    explanation: Text1000


class FieldEvidence(StrictModel):
    kind: Literal['profile_field']
    field: ProfileField


class TopicEvidence(StrictModel):
    kind: Literal['topic']
    topic: str


class PairEvidence(StrictModel):
    kind: Literal['pair']
    other_book_id: str
    dimension: Literal['overlap', 'difficulty', 'prerequisites']


Evidence = Annotated[FieldEvidence | TopicEvidence | PairEvidence, Field(discriminator='kind')]


class Judgment(StrictModel):
    book_id: str
    role: Literal['core', 'selected_chapters', 'reference', 'skip_for_now']
    rationale: Rationale
    relevance: Relevance
    depth: Depth | None
    practice: Practice | None
    focus_topics: list[str] = Field(max_length=50)
    evidence_refs: list[Evidence] = Field(max_length=20)
    reviewed: bool = Field(strict=True)

    @field_validator('book_id')
    @classmethod
    def canonical_id(cls, value):
        if str(UUID(value)) != value:
            raise ValueError('A canonical book UUID is required.')
        return value

    @field_validator('reviewed')
    @classmethod
    def confirmed(cls, value):
        if not value:
            raise ValueError('Confirm review for every selected book.')
        return value


class ComparisonRequest(StrictModel):
    input_token: Token
    expected_revision: int | None = Field(ge=1, strict=True)
    books: list[Judgment] = Field(min_length=3, max_length=5)


class GoalInput(StrictModel):
    id: str
    title: str
    description: str | None
    updated_at: str
    book_ids: list[str]


class BookInput(StrictModel):
    book_id: str
    title: str
    profile: BookProfileResponse
    topic_keys: list[str]
    topic_count: int
    unique_topics: list[str]


class Coverage(StrictModel):
    topic: str
    book_ids: list[str]


class SetComparison(StrictModel):
    shared: list[str]
    left_only: list[str]
    right_only: list[str]


class PairComparison(StrictModel):
    left_book_id: str
    right_book_id: str
    overlap: SetComparison
    difficulty: Literal['lower', 'same', 'higher', 'unknown']
    prerequisites: SetComparison | None


class ComparisonPreview(StrictModel):
    goal: GoalInput
    books: list[BookInput]
    coverage: list[Coverage]
    pairs: list[PairComparison]
    algorithm_version: str
    derived_source: Literal['derived']


class ManualProvenance(StrictModel):
    role: Literal['manual']
    rationale: Literal['manual']
    relevance: Literal['manual']
    depth: Literal['manual'] | None
    practice: Literal['manual'] | None
    focus_topics: Literal['manual'] | None
    evidence_refs: Literal['manual'] | None


class SavedJudgment(Judgment):
    provenance: ManualProvenance


class ComparisonSnapshot(StrictModel):
    preview: ComparisonPreview
    books: list[SavedJudgment] = Field(min_length=3, max_length=5)
    revision: int = Field(ge=1)
    input_token: Token
    created_at: str
    updated_at: str


class ReadinessIssue(StrictModel):
    code: Literal['goal_inactive', 'invalid_book_selection', 'book_missing',
                  'profile_missing', 'topics_missing']
    book_id: str | None = None
    message: str


class Readiness(StrictModel):
    ready: bool
    issues: list[ReadinessIssue]


class ComparisonEnvelope(StrictModel):
    goal_id: str
    is_active: bool
    readiness: Readiness
    input_token: str | None
    current: ComparisonPreview | None
    saved: ComparisonSnapshot | None
    stale: bool
    stale_reasons: list[str]

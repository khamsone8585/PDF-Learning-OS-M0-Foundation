from typing import Literal

from pydantic import BaseModel, ConfigDict

Difficulty = Literal['beginner', 'intermediate', 'advanced']
Orientation = Literal['theory_heavy', 'balanced', 'practice_heavy']
Source = Literal['manual', 'ai_generated', 'ai_assisted', 'derived']


class BookProfileRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    domain: str | None
    difficulty: Difficulty | None
    prerequisites: list[str]
    main_topics: list[str]
    orientation: Orientation | None
    strengths: list[str]
    weaknesses: list[str]
    suggested_use: str | None


class BookProfileProvenance(BaseModel):
    domain: Source | None
    difficulty: Source | None
    prerequisites: Source | None
    main_topics: Source | None
    orientation: Source | None
    strengths: Source | None
    weaknesses: Source | None
    suggested_use: Source | None


class BookProfileResponse(BookProfileRequest):
    book_id: str
    provenance: BookProfileProvenance
    created_at: str
    updated_at: str


class BookProfileEnvelope(BaseModel):
    profile: BookProfileResponse | None

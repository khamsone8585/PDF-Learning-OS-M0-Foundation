from pydantic import BaseModel, Field


class ChapterResponse(BaseModel):
    id: str
    title: str
    position: int
    level: int
    start_page: int
    end_page: int
    source: str


class ChaptersResponse(BaseModel):
    book_id: str
    processing_status: str
    content_available: bool
    toc_status: str | None
    structure_source: str | None
    chapters: list[ChapterResponse]


class ManualSection(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    start_page: int = Field(ge=1)


class ManualChaptersRequest(BaseModel):
    sections: list[ManualSection] = Field(min_length=1)

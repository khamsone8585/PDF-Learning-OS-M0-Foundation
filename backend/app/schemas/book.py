from pydantic import BaseModel


class ProcessingError(BaseModel):
    code: str
    message: str


class BookResponse(BaseModel):
    id: str
    title: str
    original_filename: str
    author: str | None
    edition: str | None
    year: int | None
    page_count: int
    imported_at: str
    size_bytes: int
    file_available: bool
    processing_status: str
    processing_error: ProcessingError | None
    processing_started_at: str | None
    processed_at: str | None
    has_processed_content: bool
    toc_status: str | None


class BooksResponse(BaseModel):
    books: list[BookResponse]

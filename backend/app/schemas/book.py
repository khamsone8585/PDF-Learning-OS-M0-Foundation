from pydantic import BaseModel


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


class BooksResponse(BaseModel):
    books: list[BookResponse]

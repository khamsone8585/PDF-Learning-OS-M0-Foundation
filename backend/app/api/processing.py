from fastapi import APIRouter, Request

from app.api.books import invoke, library
from app.schemas.book import BookResponse
from app.schemas.processing import ChaptersResponse, ManualChaptersRequest
from app.services.library_storage import canonical_id

router = APIRouter()


def processor(request):
    library(request)
    return request.app.state.processing


@router.post('/books/{book_id}/process', response_model=BookResponse)
async def process_book(book_id: str, request: Request):
    return await invoke(processor(request).process, canonical_id(book_id))


@router.get('/books/{book_id}/chapters', response_model=ChaptersResponse)
async def chapters(book_id: str, request: Request):
    return await invoke(processor(request).chapters, canonical_id(book_id))


@router.put('/books/{book_id}/chapters', response_model=ChaptersResponse)
async def correct_chapters(book_id: str, body: ManualChaptersRequest, request: Request):
    return await invoke(processor(request).correct_chapters, canonical_id(book_id), body.sections)

from fastapi import APIRouter, Request

from app.api.books import invoke, library
from app.schemas.book_profile import BookProfileEnvelope, BookProfileRequest, BookProfileResponse
from app.services.library_storage import canonical_id

router = APIRouter()


def profiles(request):
    library(request)
    return request.app.state.book_profiles


@router.get('/books/{book_id}/profile', response_model=BookProfileEnvelope)
async def get_profile(book_id: str, request: Request):
    return await invoke(profiles(request).get, canonical_id(book_id))


@router.put('/books/{book_id}/profile', response_model=BookProfileResponse)
async def put_profile(book_id: str, body: BookProfileRequest, request: Request):
    return await invoke(profiles(request).put, canonical_id(book_id), body)

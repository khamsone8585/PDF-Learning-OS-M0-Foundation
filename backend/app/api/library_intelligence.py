from typing import Literal

from fastapi import APIRouter, Query, Request

from app.api.books import invoke, library
from app.schemas.library_intelligence import (LibraryMapResponse, PrerequisitePage,
                                              RelationPage, RelationReviewRequest,
                                              RelationReviewResponse)

router = APIRouter()


def intelligence(request):
    library(request)
    return request.app.state.library_intelligence


@router.get('/library-intelligence/map', response_model=LibraryMapResponse)
async def library_map(request: Request):
    return await invoke(intelligence(request).map)


@router.get('/library-intelligence/relations', response_model=RelationPage)
async def relations(request: Request, kind: Literal['bibliographic', 'topic_overlap'],
                    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                    book_id: str | None = None):
    return await invoke(intelligence(request).relations, kind, offset, limit, book_id)


@router.get('/library-intelligence/prerequisites', response_model=PrerequisitePage)
async def prerequisites(request: Request, offset: int = Query(0, ge=0),
                        limit: int = Query(50, ge=1, le=100), book_id: str | None = None):
    return await invoke(intelligence(request).prerequisites, offset, limit, book_id)


@router.put('/library-intelligence/relation-reviews', response_model=RelationReviewResponse)
async def review_relation(body: RelationReviewRequest, request: Request):
    return await invoke(intelligence(request).review, body)

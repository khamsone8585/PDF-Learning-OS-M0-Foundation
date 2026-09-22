from fastapi import APIRouter, Request

from app.api.books import invoke, library
from app.schemas.book_comparison import ComparisonEnvelope, ComparisonRequest
from app.services.learning_goals import canonical_goal_id

router = APIRouter()


def comparisons(request):
    library(request)
    return request.app.state.book_comparisons


@router.get('/learning-goals/{goal_id}/comparison', response_model=ComparisonEnvelope)
async def get_comparison(goal_id: str, request: Request):
    return await invoke(comparisons(request).get, canonical_goal_id(goal_id))


@router.put('/learning-goals/{goal_id}/comparison', response_model=ComparisonEnvelope)
async def put_comparison(goal_id: str, body: ComparisonRequest, request: Request):
    return await invoke(comparisons(request).put, canonical_goal_id(goal_id), body)

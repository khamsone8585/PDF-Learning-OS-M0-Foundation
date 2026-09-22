from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.books import invoke, library
from app.schemas.learning_goal import (ActiveLearningGoalResponse, LearningGoalBooksRequest,
                                       LearningGoalRequest, LearningGoalResponse)
from app.services.learning_goals import canonical_goal_id

router = APIRouter()


def goals(request):
    library(request)
    return request.app.state.learning_goals


@router.post('/learning-goals', response_model=LearningGoalResponse, status_code=201)
async def create_goal(body: LearningGoalRequest, request: Request):
    result = await invoke(goals(request).create, body.title, body.description, body.book_ids)
    return JSONResponse(result, status_code=201,
                        headers={'Location': f"/learning-goals/{result['id']}"})


@router.get('/learning-goals/active', response_model=ActiveLearningGoalResponse)
async def active_goal(request: Request):
    return await invoke(goals(request).active)


@router.put('/learning-goals/{goal_id}/books', response_model=LearningGoalResponse)
async def replace_goal_books(goal_id: str, body: LearningGoalBooksRequest, request: Request):
    return await invoke(goals(request).replace_books, canonical_goal_id(goal_id), body.book_ids)

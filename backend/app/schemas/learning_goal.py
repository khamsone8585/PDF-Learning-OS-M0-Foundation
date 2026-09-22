from pydantic import BaseModel


class LearningGoalRequest(BaseModel):
    title: str
    description: str | None = None
    book_ids: list[str]


class LearningGoalBooksRequest(BaseModel):
    book_ids: list[str]


class LearningGoalResponse(BaseModel):
    id: str
    title: str
    description: str | None
    is_active: bool
    created_at: str
    updated_at: str
    book_ids: list[str]


class ActiveLearningGoalResponse(BaseModel):
    goal: LearningGoalResponse | None

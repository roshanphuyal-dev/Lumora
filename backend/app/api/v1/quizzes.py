import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.quiz import QuizCreate, QuizRead
from app.services import quiz_service

router = APIRouter(prefix="/notebooks/{notebook_id}/quizzes", tags=["quizzes"])
Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)


@router.post("", response_model=QuizRead, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    notebook_id: uuid.UUID,
    payload: QuizCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> QuizRead:
    quiz = await quiz_service.create_quiz(db, current_user.id, notebook_id, payload)
    return QuizRead.model_validate(quiz)


@router.get("", response_model=Page[QuizRead])
async def list_quizzes(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> Page[QuizRead]:
    page = await quiz_service.list_quizzes(db, current_user.id, notebook_id, limit, offset)
    return Page[QuizRead](
        items=[QuizRead.model_validate(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{quiz_id}", response_model=QuizRead)
async def get_quiz(
    notebook_id: uuid.UUID, quiz_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> QuizRead:
    quiz = await quiz_service.get_owned_quiz(db, current_user.id, notebook_id, quiz_id)
    return QuizRead.model_validate(quiz)


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    notebook_id: uuid.UUID, quiz_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    await quiz_service.delete_quiz(db, current_user.id, notebook_id, quiz_id)

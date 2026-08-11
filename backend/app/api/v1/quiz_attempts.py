import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.quiz_attempt import (
    QuizAttemptAnswerPatch,
    QuizAttemptRead,
    QuizAttemptReviewRead,
    QuizAttemptSummary,
)
from app.services import quiz_attempt_service

router = APIRouter(
    prefix="/notebooks/{notebook_id}/quizzes/{quiz_id}/attempts", tags=["quiz-attempts"]
)
Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)


@router.post("", response_model=QuizAttemptRead, status_code=status.HTTP_201_CREATED)
async def start_attempt(
    notebook_id: uuid.UUID, quiz_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> QuizAttemptRead | QuizAttemptReviewRead:
    attempt = await quiz_attempt_service.start_attempt(db, current_user.id, notebook_id, quiz_id)
    return await quiz_attempt_service.get_attempt(
        db, current_user.id, notebook_id, quiz_id, attempt.id
    )


@router.get("", response_model=Page[QuizAttemptSummary])
async def list_attempts(
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> Page[QuizAttemptSummary]:
    page = await quiz_attempt_service.list_attempts(
        db, current_user.id, notebook_id, quiz_id, limit, offset
    )
    return Page[QuizAttemptSummary](
        items=[QuizAttemptSummary.model_validate(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{attempt_id}", response_model=QuizAttemptRead | QuizAttemptReviewRead)
async def get_attempt(
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> QuizAttemptRead | QuizAttemptReviewRead:
    return await quiz_attempt_service.get_attempt(
        db, current_user.id, notebook_id, quiz_id, attempt_id
    )


@router.patch("/{attempt_id}", response_model=QuizAttemptRead)
async def autosave_answer(
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    payload: QuizAttemptAnswerPatch,
    current_user: CurrentUser,
    db: DbSession,
) -> QuizAttemptRead | QuizAttemptReviewRead:
    await quiz_attempt_service.autosave_answer(
        db,
        current_user.id,
        notebook_id,
        quiz_id,
        attempt_id,
        payload.question_id,
        payload.answer,
    )
    return await quiz_attempt_service.get_attempt(
        db, current_user.id, notebook_id, quiz_id, attempt_id
    )


@router.post("/{attempt_id}/submit", response_model=QuizAttemptRead | QuizAttemptReviewRead)
async def submit_attempt(
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> QuizAttemptRead | QuizAttemptReviewRead:
    await quiz_attempt_service.submit_attempt(db, current_user.id, notebook_id, quiz_id, attempt_id)
    return await quiz_attempt_service.get_attempt(
        db, current_user.id, notebook_id, quiz_id, attempt_id
    )

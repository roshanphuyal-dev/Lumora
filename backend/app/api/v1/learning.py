import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.learning import (
    ActivityAnalyticsRead,
    NotebookProgressRead,
    QuizPerformanceRead,
    RevisionHistoryItem,
    StudyActivityCreate,
    StudyActivityRead,
    TopicMasteryRead,
)
from app.services import learning_service

router = APIRouter(prefix="/notebooks/{notebook_id}", tags=["progress"])
user_router = APIRouter(prefix="/users/me/analytics", tags=["progress"])
Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)


def _require_personalization() -> None:
    if not get_settings().personalization_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personalization is not available",
        )


@router.get("/progress", response_model=NotebookProgressRead)
async def get_progress(
    notebook_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> NotebookProgressRead:
    _require_personalization()
    return await learning_service.get_notebook_progress(db, current_user.id, notebook_id)


@router.get("/mastery", response_model=Page[TopicMasteryRead])
async def list_mastery(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> Page[TopicMasteryRead]:
    _require_personalization()
    page = await learning_service.list_topic_mastery(
        db, current_user.id, notebook_id, limit, offset
    )
    return Page[TopicMasteryRead](
        items=page.items, total=page.total, limit=page.limit, offset=page.offset
    )


@router.get("/analytics/quiz-performance", response_model=QuizPerformanceRead)
async def get_quiz_performance(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> QuizPerformanceRead:
    _require_personalization()
    return await learning_service.get_quiz_performance(
        db, current_user.id, notebook_id, limit, offset
    )


@router.post("/activities", response_model=StudyActivityRead, status_code=status.HTTP_201_CREATED)
async def record_activity(
    notebook_id: uuid.UUID,
    payload: StudyActivityCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> StudyActivityRead:
    _require_personalization()
    activity = await learning_service.record_study_activity(
        db, current_user.id, notebook_id, payload
    )
    return StudyActivityRead.model_validate(activity, from_attributes=True)


@router.get("/analytics/activity", response_model=ActivityAnalyticsRead)
async def get_notebook_activity_analytics(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(default=90, ge=1, le=366),
) -> ActivityAnalyticsRead:
    _require_personalization()
    return await learning_service.get_activity_analytics(
        db, current_user.id, notebook_id=notebook_id, days=days
    )


@router.get("/revision-history", response_model=Page[RevisionHistoryItem])
async def list_revision_history(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> Page[RevisionHistoryItem]:
    _require_personalization()
    page = await learning_service.list_revision_history(
        db, current_user.id, notebook_id, limit, offset
    )
    return Page[RevisionHistoryItem](
        items=page.items, total=page.total, limit=page.limit, offset=page.offset
    )


@user_router.get("/activity", response_model=ActivityAnalyticsRead)
async def get_user_activity_analytics(
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(default=90, ge=1, le=366),
) -> ActivityAnalyticsRead:
    _require_personalization()
    return await learning_service.get_activity_analytics(
        db, current_user.id, notebook_id=None, days=days
    )

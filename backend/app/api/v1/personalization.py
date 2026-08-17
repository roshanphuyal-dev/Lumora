import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.personalization import (
    LearningPreferenceRead,
    LearningPreferenceSuggestionRead,
    LearningPreferenceUpdate,
    RecommendationRead,
)
from app.services import personalization_service

preferences_router = APIRouter(prefix="/users/me", tags=["personalization"])
recommendations_router = APIRouter(
    prefix="/notebooks/{notebook_id}/recommendations", tags=["personalization"]
)


def _require_personalization() -> None:
    if not get_settings().personalization_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personalization is not available",
        )


@preferences_router.get("/learning-preferences", response_model=LearningPreferenceRead)
async def get_learning_preferences(
    current_user: CurrentUser, db: DbSession
) -> LearningPreferenceRead:
    _require_personalization()
    return await personalization_service.get_preferences(db, current_user.id)


@preferences_router.patch("/learning-preferences", response_model=LearningPreferenceRead)
async def update_learning_preferences(
    payload: LearningPreferenceUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> LearningPreferenceRead:
    _require_personalization()
    preference = await personalization_service.update_preferences(db, current_user.id, payload)
    return LearningPreferenceRead.model_validate(preference)


@preferences_router.get(
    "/learning-preference-suggestions",
    response_model=list[LearningPreferenceSuggestionRead],
)
async def list_learning_preference_suggestions(
    current_user: CurrentUser, db: DbSession
) -> list[LearningPreferenceSuggestionRead]:
    _require_personalization()
    suggestions = await personalization_service.list_suggestions(db, current_user.id)
    return [LearningPreferenceSuggestionRead.model_validate(item) for item in suggestions]


@preferences_router.post(
    "/learning-preference-suggestions/refresh",
    response_model=list[LearningPreferenceSuggestionRead],
)
async def refresh_learning_preference_suggestions(
    current_user: CurrentUser, db: DbSession
) -> list[LearningPreferenceSuggestionRead]:
    _require_personalization()
    suggestions = await personalization_service.refresh_suggestions(db, current_user.id)
    return [LearningPreferenceSuggestionRead.model_validate(item) for item in suggestions]


@preferences_router.post(
    "/learning-preference-suggestions/{suggestion_id}/accept",
    response_model=LearningPreferenceSuggestionRead,
)
async def accept_learning_preference_suggestion(
    suggestion_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> LearningPreferenceSuggestionRead:
    _require_personalization()
    suggestion = await personalization_service.resolve_suggestion(
        db, current_user.id, suggestion_id, accept=True
    )
    return LearningPreferenceSuggestionRead.model_validate(suggestion)


@preferences_router.post(
    "/learning-preference-suggestions/{suggestion_id}/reject",
    response_model=LearningPreferenceSuggestionRead,
)
async def reject_learning_preference_suggestion(
    suggestion_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> LearningPreferenceSuggestionRead:
    _require_personalization()
    suggestion = await personalization_service.resolve_suggestion(
        db, current_user.id, suggestion_id, accept=False
    )
    return LearningPreferenceSuggestionRead.model_validate(suggestion)


@recommendations_router.get("", response_model=list[RecommendationRead])
async def list_recommendations(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[RecommendationRead]:
    _require_personalization()
    return await personalization_service.list_recommendations(
        db, current_user.id, notebook_id, limit
    )

import uuid
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook
from app.models.personalization import LearningPreference, LearningPreferenceSuggestion
from app.schemas.learning import TopicMasteryRead
from app.schemas.personalization import (
    LearningPreferenceRead,
    LearningPreferenceUpdate,
    RecommendationRead,
)
from app.services import learning_service
from app.services.notebook_service import get_owned_notebook


async def get_preferences(db: AsyncSession, user_id: uuid.UUID) -> LearningPreferenceRead:
    preference = await db.scalar(
        select(LearningPreference).where(LearningPreference.user_id == user_id)
    )
    if preference is None:
        return LearningPreferenceRead(user_id=user_id)
    return LearningPreferenceRead.model_validate(preference)


async def update_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: LearningPreferenceUpdate,
) -> LearningPreference:
    preference = await db.scalar(
        select(LearningPreference).where(LearningPreference.user_id == user_id)
    )
    if preference is None:
        preference = LearningPreference(user_id=user_id)
        db.add(preference)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(preference, key, value)
    await db.commit()
    await db.refresh(preference)
    return preference


async def list_suggestions(
    db: AsyncSession, user_id: uuid.UUID
) -> list[LearningPreferenceSuggestion]:
    return list(
        await db.scalars(
            select(LearningPreferenceSuggestion)
            .where(
                LearningPreferenceSuggestion.user_id == user_id,
                LearningPreferenceSuggestion.status == "pending",
            )
            .order_by(LearningPreferenceSuggestion.created_at.desc())
        )
    )


async def refresh_suggestions(
    db: AsyncSession, user_id: uuid.UUID
) -> list[LearningPreferenceSuggestion]:
    """Create pending suggestions only from fixed, inspectable mastery thresholds."""
    notebook_ids = list(await db.scalars(select(Notebook.id).where(Notebook.owner_id == user_id)))
    masteries: list[TopicMasteryRead] = []
    for notebook_id in notebook_ids:
        page = await learning_service.list_topic_mastery(db, user_id, notebook_id, 10_000, 0)
        masteries.extend(page.items)
    low_mastery_count = sum(
        item.mastery_percent < 40 and item.confidence >= 0.2 for item in masteries
    )
    if low_mastery_count >= 2:
        await _create_pending_suggestion(
            db,
            user_id,
            preference_key="explanation_depth",
            suggested_value="detailed",
            signal_type="multiple_low_mastery_topics",
            rationale=(
                f"You have {low_mastery_count} topics below 40% mastery with sufficient "
                "evidence. Detailed explanations may make review easier."
            ),
        )
    await db.commit()
    return await list_suggestions(db, user_id)


async def _create_pending_suggestion(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    preference_key: str,
    suggested_value: str,
    signal_type: str,
    rationale: str,
) -> None:
    existing = await db.scalar(
        select(LearningPreferenceSuggestion).where(
            LearningPreferenceSuggestion.user_id == user_id,
            LearningPreferenceSuggestion.preference_key == preference_key,
            LearningPreferenceSuggestion.suggested_value == suggested_value,
            LearningPreferenceSuggestion.signal_type == signal_type,
        )
    )
    if existing is None:
        db.add(
            LearningPreferenceSuggestion(
                user_id=user_id,
                preference_key=preference_key,
                suggested_value=suggested_value,
                signal_type=signal_type,
                rationale=rationale,
                status="pending",
            )
        )


async def resolve_suggestion(
    db: AsyncSession,
    user_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    *,
    accept: bool,
) -> LearningPreferenceSuggestion:
    suggestion = await db.scalar(
        select(LearningPreferenceSuggestion).where(
            LearningPreferenceSuggestion.id == suggestion_id,
            LearningPreferenceSuggestion.user_id == user_id,
        )
    )
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Suggestion has already been resolved",
        )
    suggestion.status = "accepted" if accept else "rejected"
    if accept:
        await update_preferences(
            db,
            user_id,
            LearningPreferenceUpdate(**{suggestion.preference_key: suggestion.suggested_value}),
        )
    else:
        await db.commit()
    await db.refresh(suggestion)
    return suggestion


async def list_recommendations(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    limit: int,
) -> list[RecommendationRead]:
    """Select every action and immutable field deterministically from mastery."""
    await get_owned_notebook(db, user_id, notebook_id)
    page = await learning_service.list_topic_mastery(db, user_id, notebook_id, 10_000, 0)
    masteries = sorted(page.items, key=lambda item: (item.mastery_percent, item.topic))[:limit]
    return [_recommendation(notebook_id, mastery) for mastery in masteries]


def _recommendation(notebook_id: uuid.UUID, mastery: TopicMasteryRead) -> RecommendationRead:
    percent = mastery.mastery_percent
    query = urlencode({"topic": mastery.topic})
    if percent < 40:
        action = "review_topic"
        priority = "high"
        tab = "notes"
        rationale = f"Mastery is {percent:.0f}%, below the 40% review threshold."
    elif percent < 70:
        action = "take_quiz"
        priority = "medium"
        tab = "quizzes"
        rationale = f"Mastery is {percent:.0f}%; targeted practice can reinforce this topic."
    else:
        action = "practice_challenge"
        priority = "low"
        tab = "quizzes"
        rationale = f"Mastery is {percent:.0f}%; a harder challenge can extend retention."
    return RecommendationRead(
        action=action,
        priority=priority,
        topic=mastery.topic,
        url=f"/notebooks/{notebook_id}?tab={tab}&{query}",
        rationale=rationale,
    )

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.learning import TopicMastery
from app.models.notebook import Notebook
from app.models.personalization import LearningPreference, LearningPreferenceSuggestion
from app.models.user import User
from app.schemas.course import PageResult
from app.schemas.learning import TopicMasteryRead
from app.schemas.personalization import LearningPreferenceUpdate
from app.services import personalization_service


async def _register_headers(client: AsyncClient, email: str) -> dict[str, str]:
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-1", "full_name": "Learner"},
    )
    assert registration.status_code == 201, registration.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _user_and_notebook(db: AsyncSession, email: str) -> tuple[User, Notebook]:
    user = User(email=email, full_name="Learner")
    db.add(user)
    await db.flush()
    notebook = Notebook(owner_id=user.id, name="Biology")
    db.add(notebook)
    await db.commit()
    return user, notebook


async def test_pending_suggestion_does_not_change_preferences_until_accepted(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, notebook = await _user_and_notebook(db_session, "suggestion@example.com")
    now = datetime.now(UTC)
    db_session.add_all(
        [
            TopicMastery(
                user_id=user.id,
                notebook_id=notebook.id,
                topic=topic,
                mastery_percent=Decimal("30"),
                confidence=Decimal("0.4"),
                evidence_weight=Decimal("2"),
                evidence_count=3,
                calculated_at=now,
            )
            for topic in ("Mitosis", "Meiosis")
        ]
    )
    await db_session.commit()

    async def live_mastery(*_args, **_kwargs):
        return PageResult(
            items=[
                TopicMasteryRead(
                    topic=topic,
                    mastery_percent=30,
                    confidence=0.4,
                    evidence_weight=2,
                    evidence_count=3,
                    calculated_at=now,
                )
                for topic in ("Mitosis", "Meiosis")
            ],
            total=2,
            limit=10_000,
            offset=0,
        )

    monkeypatch.setattr(
        personalization_service.learning_service, "list_topic_mastery", live_mastery
    )

    suggestions = await personalization_service.refresh_suggestions(db_session, user.id)
    assert len(suggestions) == 1
    assert suggestions[0].status == "pending"
    assert (
        await personalization_service.get_preferences(db_session, user.id)
    ).explanation_depth is None

    await personalization_service.resolve_suggestion(
        db_session, user.id, suggestions[0].id, accept=True
    )
    assert (
        await personalization_service.get_preferences(db_session, user.id)
    ).explanation_depth == "detailed"
    assert (await db_session.scalar(select(LearningPreferenceSuggestion))).status == "accepted"


async def test_rejected_suggestion_never_changes_preferences(db_session: AsyncSession) -> None:
    user, _ = await _user_and_notebook(db_session, "reject@example.com")
    suggestion = LearningPreferenceSuggestion(
        user_id=user.id,
        preference_key="explanation_style",
        suggested_value="step_by_step",
        signal_type="test_signal",
        rationale="Deterministic test rationale.",
        status="pending",
    )
    db_session.add(suggestion)
    await db_session.commit()

    await personalization_service.resolve_suggestion(
        db_session, user.id, suggestion.id, accept=False
    )
    assert (
        await personalization_service.get_preferences(db_session, user.id)
    ).explanation_style is None
    assert suggestion.status == "rejected"


async def test_preferences_and_suggestions_are_owner_scoped(db_session: AsyncSession) -> None:
    owner, _ = await _user_and_notebook(db_session, "preference-owner@example.com")
    intruder, _ = await _user_and_notebook(db_session, "preference-intruder@example.com")
    await personalization_service.update_preferences(
        db_session, owner.id, LearningPreferenceUpdate(explanation_style="socratic")
    )
    suggestion = LearningPreferenceSuggestion(
        user_id=owner.id,
        preference_key="explanation_depth",
        suggested_value="concise",
        signal_type="test_signal",
        rationale="Deterministic test rationale.",
        status="pending",
    )
    db_session.add(suggestion)
    await db_session.commit()

    assert (
        await personalization_service.get_preferences(db_session, intruder.id)
    ).explanation_style is None
    assert await personalization_service.list_suggestions(db_session, intruder.id) == []
    with pytest.raises(HTTPException) as exc_info:
        await personalization_service.resolve_suggestion(
            db_session, intruder.id, suggestion.id, accept=True
        )
    assert exc_info.value.status_code == 404


async def test_recommendations_are_deterministic_and_owner_scoped(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, notebook = await _user_and_notebook(db_session, "recommend-owner@example.com")
    intruder, _ = await _user_and_notebook(db_session, "recommend-intruder@example.com")
    now = datetime.now(UTC)
    for topic, mastery in (("Cell cycle", "35"), ("DNA repair", "55"), ("Genetics", "80")):
        db_session.add(
            TopicMastery(
                user_id=owner.id,
                notebook_id=notebook.id,
                topic=topic,
                mastery_percent=Decimal(mastery),
                confidence=Decimal("0.5"),
                evidence_weight=Decimal("2.5"),
                evidence_count=4,
                calculated_at=now,
            )
        )
    await db_session.commit()

    async def live_mastery(*_args, **_kwargs):
        return PageResult(
            items=[
                TopicMasteryRead(
                    topic=topic,
                    mastery_percent=float(mastery),
                    confidence=0.5,
                    evidence_weight=2.5,
                    evidence_count=4,
                    calculated_at=now,
                )
                for topic, mastery in (
                    ("Cell cycle", "35"),
                    ("DNA repair", "55"),
                    ("Genetics", "80"),
                )
            ],
            total=3,
            limit=10_000,
            offset=0,
        )

    monkeypatch.setattr(
        personalization_service.learning_service, "list_topic_mastery", live_mastery
    )

    recommendations = await personalization_service.list_recommendations(
        db_session, owner.id, notebook.id, 10
    )
    assert [(item.action, item.priority, item.topic) for item in recommendations] == [
        ("review_topic", "high", "Cell cycle"),
        ("take_quiz", "medium", "DNA repair"),
        ("practice_challenge", "low", "Genetics"),
    ]
    assert recommendations[0].url == f"/notebooks/{notebook.id}?tab=notes&topic=Cell+cycle"
    assert recommendations[0].rationale == "Mastery is 35%, below the 40% review threshold."
    with pytest.raises(HTTPException) as exc_info:
        await personalization_service.list_recommendations(db_session, intruder.id, notebook.id, 10)
    assert exc_info.value.status_code == 404


async def test_aged_snapshot_does_not_control_recommendation_or_suggestion_band(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, notebook = await _user_and_notebook(db_session, "aged-mastery@example.com")
    now = datetime.now(UTC)
    db_session.add(
        TopicMastery(
            user_id=user.id,
            notebook_id=notebook.id,
            topic="Genetics",
            mastery_percent=Decimal("85"),
            confidence=Decimal("0.8"),
            evidence_weight=Decimal("4"),
            evidence_count=5,
            calculated_at=now,
        )
    )
    await db_session.commit()

    async def decayed_mastery(*_args, **_kwargs):
        return PageResult(
            items=[
                TopicMasteryRead(
                    topic="Genetics",
                    mastery_percent=55,
                    confidence=0.1,
                    evidence_weight=0.5,
                    evidence_count=5,
                    calculated_at=now,
                )
            ],
            total=1,
            limit=10_000,
            offset=0,
        )

    monkeypatch.setattr(
        personalization_service.learning_service, "list_topic_mastery", decayed_mastery
    )

    recommendations = await personalization_service.list_recommendations(
        db_session, user.id, notebook.id, 10
    )
    suggestions = await personalization_service.refresh_suggestions(db_session, user.id)

    assert recommendations[0].action == "take_quiz"
    assert recommendations[0].priority == "medium"
    assert suggestions == []


async def test_suggestion_creation_is_idempotent(db_session: AsyncSession) -> None:
    user, _ = await _user_and_notebook(db_session, "idempotent-suggestion@example.com")
    for rationale in ("First rationale.", "Second rationale."):
        await personalization_service._create_pending_suggestion(
            db_session,
            user.id,
            preference_key="explanation_depth",
            suggested_value="detailed",
            signal_type="multiple_low_mastery_topics",
            rationale=rationale,
        )
        await db_session.commit()
    assert len(list(await db_session.scalars(select(LearningPreferenceSuggestion)))) == 1
    assert len(list(await db_session.scalars(select(LearningPreference)))) == 0


async def test_personalization_api_is_default_off(client: AsyncClient, unique_email: str) -> None:
    headers = await _register_headers(client, unique_email)
    settings = get_settings()
    previous = settings.personalization_enabled
    settings.personalization_enabled = False
    try:
        response = await client.get("/api/v1/users/me/learning-preferences", headers=headers)
    finally:
        settings.personalization_enabled = previous
    assert response.status_code == 404
    assert response.json()["detail"] == "Personalization is not available"


async def test_explicit_preferences_round_trip_through_api(
    client: AsyncClient, unique_email: str
) -> None:
    headers = await _register_headers(client, unique_email)
    settings = get_settings()
    previous = settings.personalization_enabled
    settings.personalization_enabled = True
    try:
        updated = await client.patch(
            "/api/v1/users/me/learning-preferences",
            headers=headers,
            json={"explanation_depth": "concise", "explanation_style": "socratic"},
        )
        fetched = await client.get("/api/v1/users/me/learning-preferences", headers=headers)
    finally:
        settings.personalization_enabled = previous
    assert updated.status_code == 200, updated.text
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["explanation_depth"] == "concise"
    assert fetched.json()["explanation_style"] == "socratic"

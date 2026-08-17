import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.learning import LearningEvidence, StudyActivity, TopicMastery
from app.models.notebook import Notebook
from app.models.quiz import Question, QuestionType, Quiz, QuizDifficulty, QuizStatus
from app.models.quiz_attempt import QuizAttempt, QuizAttemptAnswer, QuizAttemptStatus
from app.models.user import User
from app.schemas.learning import StudyActivityCreate
from app.services import learning_service, quiz_attempt_service


async def _register(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-1", "full_name": "Learner"},
    )
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correct-horse-1"}
    )
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_calculate_mastery_uses_exact_adr_0014_formula() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    result = learning_service.calculate_mastery(
        [
            (1.0, "easy", now),
            (0.0, "hard", now - timedelta(days=30)),
            (0.5, "mixed", now - timedelta(days=60)),
        ],
        now=now,
    )

    # Weights: .75, .625, .25. Weighted score: .75 + 0 + .125.
    assert result.evidence_weight == pytest.approx(1.625)
    assert result.mastery_percent == pytest.approx((1 + 0.875) / (2 + 1.625) * 100)
    assert result.confidence == pytest.approx(1.625 / 5)
    assert result.evidence_count == 3


def test_calculate_streaks_handles_current_and_longest_runs() -> None:
    today = datetime(2026, 8, 17, tzinfo=UTC).date()
    current, longest = learning_service.calculate_streaks(
        [
            today - timedelta(days=6),
            today - timedelta(days=5),
            today - timedelta(days=2),
            today - timedelta(days=1),
            today,
        ],
        today=today,
    )
    assert current == 3
    assert longest == 3


def test_calculate_streaks_expires_after_a_missed_day() -> None:
    today = datetime(2026, 8, 17, tzinfo=UTC).date()
    assert learning_service.calculate_streaks(
        [today - timedelta(days=4), today - timedelta(days=3)], today=today
    ) == (0, 2)


async def _learning_context(
    db: AsyncSession, email: str, topic: str = "Mitosis"
) -> tuple[User, Notebook, Quiz, Question]:
    user = User(email=email, full_name="Learner")
    db.add(user)
    await db.flush()
    notebook = Notebook(owner_id=user.id, name="Biology")
    db.add(notebook)
    await db.flush()
    quiz = Quiz(
        notebook_id=notebook.id,
        user_id=user.id,
        title="Cells",
        question_types=["mcq"],
        question_count=1,
        difficulty=QuizDifficulty.MEDIUM,
        status=QuizStatus.DONE,
    )
    db.add(quiz)
    await db.flush()
    question = Question(
        quiz_id=quiz.id,
        position=0,
        question_type=QuestionType.MCQ,
        prompt="What divides?",
        type_data={},
        correct_answer="cell",
        explanation="A cell divides.",
        topic=topic,
        difficulty=QuizDifficulty.HARD,
    )
    db.add(question)
    await db.commit()
    return user, notebook, quiz, question


async def test_objective_grading_records_evidence_and_mastery_transactionally(
    db_session: AsyncSession,
) -> None:
    user, notebook, quiz, question = await _learning_context(db_session, "evidence@example.com")
    settings = get_settings()
    previous = settings.personalization_enabled
    settings.personalization_enabled = True
    try:
        attempt = await quiz_attempt_service.start_attempt(
            db_session, user.id, notebook.id, quiz.id
        )
        await quiz_attempt_service.autosave_answer(
            db_session, user.id, notebook.id, quiz.id, attempt.id, question.id, "cell"
        )
        await quiz_attempt_service.submit_attempt(
            db_session, user.id, notebook.id, quiz.id, attempt.id
        )
    finally:
        settings.personalization_enabled = previous

    evidence = await db_session.scalar(select(LearningEvidence))
    mastery = await db_session.scalar(select(TopicMastery))
    assert evidence is not None
    assert evidence.topic == "Mitosis"
    assert evidence.difficulty == "hard"
    assert evidence.score == Decimal("1.0000")
    assert mastery is not None
    assert float(mastery.mastery_percent) == pytest.approx((1 + 1.25) / (2 + 1.25) * 100, abs=0.001)
    assert float(mastery.confidence) == pytest.approx(0.25)
    activity = await db_session.scalar(select(StudyActivity))
    assert activity is not None
    assert activity.activity_type == "quiz_completed"
    assert activity.resource_id == quiz.id


async def test_evidence_recording_is_idempotent(db_session: AsyncSession) -> None:
    user, notebook, quiz, question = await _learning_context(db_session, "idempotent@example.com")
    now = datetime.now(UTC)
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        status=QuizAttemptStatus.GRADED,
        question_order=[str(question.id)],
        answers={},
        score=1,
        max_score=1,
        graded_at=now,
    )
    db_session.add(attempt)
    await db_session.flush()
    answer = QuizAttemptAnswer(
        attempt_id=attempt.id,
        question=question,
        student_answer="cell",
        is_correct=True,
        score=1,
        topic_tag="Mitosis",
    )
    db_session.add(answer)
    await db_session.flush()

    await learning_service.record_attempt_evidence(
        db_session, attempt, notebook.id, [answer], observed_at=now
    )
    await learning_service.record_attempt_evidence(
        db_session, attempt, notebook.id, [answer], observed_at=now
    )
    await db_session.commit()

    rows = list(await db_session.scalars(select(LearningEvidence)))
    assert len(rows) == 1


async def test_get_topic_mastery_matches_topic_case_insensitively(
    db_session: AsyncSession,
) -> None:
    user, notebook, quiz, question = await _learning_context(db_session, "topic-case@example.com")
    now = datetime.now(UTC)
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        status=QuizAttemptStatus.GRADED,
        question_order=[str(question.id)],
        answers={},
        score=1,
        max_score=1,
        graded_at=now,
    )
    db_session.add(attempt)
    await db_session.flush()
    answer = QuizAttemptAnswer(
        attempt_id=attempt.id,
        question=question,
        student_answer="cell",
        is_correct=True,
        score=1,
        topic_tag="Mitosis",
    )
    db_session.add(answer)
    await db_session.flush()
    await learning_service.record_attempt_evidence(
        db_session, attempt, notebook.id, [answer], observed_at=now
    )
    await db_session.commit()

    mastery = await learning_service.get_topic_mastery(
        db_session, user.id, notebook.id, "  MITOSIS "
    )
    assert mastery is not None
    assert mastery.topic == "Mitosis"
    assert mastery.evidence_count == 1


async def test_progress_queries_reject_non_owner(db_session: AsyncSession) -> None:
    owner, notebook, _, _ = await _learning_context(db_session, "owner-progress@example.com")
    intruder = User(email="intruder-progress@example.com", full_name="Intruder")
    db_session.add(intruder)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await learning_service.get_notebook_progress(db_session, intruder.id, notebook.id)
    assert exc_info.value.status_code == 404
    assert owner.id != intruder.id


async def test_quiz_performance_is_notebook_scoped(db_session: AsyncSession) -> None:
    user, notebook, quiz, _ = await _learning_context(db_session, "analytics-scope@example.com")
    other_notebook = Notebook(owner_id=user.id, name="Physics")
    db_session.add(other_notebook)
    await db_session.flush()
    other_quiz = Quiz(
        notebook_id=other_notebook.id,
        user_id=user.id,
        title="Motion",
        question_types=["mcq"],
        question_count=1,
        difficulty=QuizDifficulty.MEDIUM,
        status=QuizStatus.DONE,
    )
    db_session.add(other_quiz)
    await db_session.flush()
    now = datetime.now(UTC)
    db_session.add_all(
        [
            QuizAttempt(
                quiz_id=quiz.id,
                user_id=user.id,
                status=QuizAttemptStatus.GRADED,
                question_order=[],
                answers={},
                score=Decimal("1"),
                max_score=Decimal("2"),
                graded_at=now,
            ),
            QuizAttempt(
                quiz_id=other_quiz.id,
                user_id=user.id,
                status=QuizAttemptStatus.GRADED,
                question_order=[],
                answers={},
                score=Decimal("2"),
                max_score=Decimal("2"),
                graded_at=now,
            ),
        ]
    )
    await db_session.commit()

    analytics = await learning_service.get_quiz_performance(db_session, user.id, notebook.id, 20, 0)
    assert analytics.recent_attempts.total == 1
    assert analytics.recent_attempts.items[0].score_percent == 50


async def test_record_activity_is_idempotent_and_analytics_are_owner_scoped(
    db_session: AsyncSession,
) -> None:
    user, notebook, _, _ = await _learning_context(db_session, "activity@example.com")
    intruder = User(email="activity-intruder@example.com", full_name="Intruder")
    db_session.add(intruder)
    await db_session.commit()
    activity_key = uuid.uuid4()
    now = datetime.now(UTC)
    payload = StudyActivityCreate(
        activity_key=activity_key,
        activity_type="study_session",
        duration_seconds=900,
        occurred_at=now,
    )

    first = await learning_service.record_study_activity(db_session, user.id, notebook.id, payload)
    second = await learning_service.record_study_activity(db_session, user.id, notebook.id, payload)
    assert first.id == second.id
    assert len(list(await db_session.scalars(select(StudyActivity)))) == 1

    analytics = await learning_service.get_activity_analytics(
        db_session, user.id, notebook_id=notebook.id, days=30
    )
    assert analytics.total_study_seconds == 900
    assert analytics.active_days == 1
    assert analytics.current_streak_days == 1
    assert analytics.heatmap[0].activity_count == 1

    with pytest.raises(HTTPException) as exc_info:
        await learning_service.get_activity_analytics(
            db_session, intruder.id, notebook_id=notebook.id, days=30
        )
    assert exc_info.value.status_code == 404


async def test_revision_history_excludes_plain_study_sessions(
    db_session: AsyncSession,
) -> None:
    user, notebook, quiz, _ = await _learning_context(db_session, "history@example.com")
    now = datetime.now(UTC)
    for activity_type, resource_type, resource_id in [
        ("study_session", None, None),
        ("material_revised", "notebook", notebook.id),
        ("quiz_completed", "quiz", quiz.id),
    ]:
        await learning_service.record_study_activity(
            db_session,
            user.id,
            notebook.id,
            StudyActivityCreate(
                activity_key=uuid.uuid4(),
                activity_type=(
                    activity_type if activity_type != "quiz_completed" else "material_viewed"
                ),
                duration_seconds=60,
                occurred_at=now,
                resource_type=resource_type,
                resource_id=resource_id,
            ),
        )
    # Convert the final boundary-safe material view into the system-only event type.
    final_activity = await db_session.scalar(
        select(StudyActivity).where(StudyActivity.resource_id == quiz.id)
    )
    assert final_activity is not None
    final_activity.activity_type = "quiz_completed"
    await db_session.commit()

    history = await learning_service.list_revision_history(db_session, user.id, notebook.id, 20, 0)
    assert history.total == 2
    assert {item.activity_type for item in history.items} == {
        "material_revised",
        "quiz_completed",
    }


async def test_activity_api_is_idempotent_flagged_and_owner_scoped(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_token = await _register(client, "api-activity-owner@example.com")
    intruder_token = await _register(client, "api-activity-intruder@example.com")
    owner = await db_session.scalar(
        select(User).where(User.email == "api-activity-owner@example.com")
    )
    assert owner is not None
    notebook = Notebook(owner_id=owner.id, name="Biology")
    db_session.add(notebook)
    await db_session.commit()
    activity_key = str(uuid.uuid4())
    url = f"/api/v1/notebooks/{notebook.id}/activities"
    payload = {
        "activity_key": activity_key,
        "activity_type": "material_revised",
        "duration_seconds": 120,
        "occurred_at": datetime.now(UTC).isoformat(),
        "resource_type": "notebook",
        "resource_id": str(notebook.id),
    }
    settings = get_settings()
    previous = settings.personalization_enabled
    settings.personalization_enabled = True
    try:
        created = await client.post(url, json=payload, headers=_auth(owner_token))
        repeated = await client.post(url, json=payload, headers=_auth(owner_token))
        analytics = await client.get(
            f"/api/v1/notebooks/{notebook.id}/analytics/activity",
            headers=_auth(owner_token),
        )
        history = await client.get(
            f"/api/v1/notebooks/{notebook.id}/revision-history",
            headers=_auth(owner_token),
        )
        forbidden = await client.get(
            f"/api/v1/notebooks/{notebook.id}/analytics/activity",
            headers=_auth(intruder_token),
        )
    finally:
        settings.personalization_enabled = previous

    assert created.status_code == 201
    assert repeated.status_code == 201
    assert created.json()["id"] == repeated.json()["id"]
    assert analytics.status_code == 200
    assert analytics.json()["total_study_seconds"] == 120
    assert history.json()["total"] == 1
    assert forbidden.status_code == 404

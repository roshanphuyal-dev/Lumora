"""Tests for `app.workers.quiz_grading_tasks.grade_quiz_attempt_task`
(`_grade_quiz_attempt` / `_upsert_weak_topics`).

Only the orchestrator's `run_task` (the batched Gemini `QUIZ_GRADING` call) is mocked --
persistence of scores/feedback, the attempt-level score/max_score rollup, weak-topic
upsert, and the failure-resets-to-submitted path all run for real, same pattern as
`tests/test_quiz_tasks.py`.
"""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import AIResponse, ProviderName
from ai.orchestrator.task_types import TaskType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook
from app.models.quiz import Question, QuestionType, Quiz, QuizDifficulty, QuizStatus
from app.models.quiz_attempt import QuizAttempt, QuizAttemptAnswer, QuizAttemptStatus
from app.models.user import User
from app.models.weak_topic import WeakTopic
from app.workers.quiz_grading_tasks import _grade_quiz_attempt
from tests.conftest import TestSessionLocal


async def _user_notebook(db: AsyncSession, email: str) -> tuple[User, Notebook]:
    user = User(email=email, full_name="Test User")
    db.add(user)
    await db.flush()
    notebook = Notebook(owner_id=user.id, name="Biology")
    db.add(notebook)
    await db.commit()
    await db.refresh(user)
    await db.refresh(notebook)
    return user, notebook


async def _attempt_with_answers(
    db: AsyncSession,
    user: User,
    notebook: Notebook,
    *,
    objective_is_correct: bool,
) -> tuple[QuizAttempt, Question, Question]:
    """Build a quiz with one already-graded objective question (Milestone 7 grades those
    synchronously in `submit_attempt`) and one pending free-text question (score=0,
    is_correct=None -- what `submit_attempt` leaves for this task to fill in), in a
    GRADING attempt, matching the real handoff shape.
    """
    quiz = Quiz(
        notebook_id=notebook.id,
        user_id=user.id,
        title="Cell Biology",
        question_types=["mcq", "short_answer"],
        question_count=2,
        difficulty=QuizDifficulty.MEDIUM,
        status=QuizStatus.DONE,
    )
    db.add(quiz)
    await db.flush()

    objective_q = Question(
        quiz_id=quiz.id,
        position=0,
        question_type=QuestionType.MCQ,
        prompt="Powerhouse of the cell?",
        type_data={"options": ["Nucleus", "Mitochondria"]},
        correct_answer="Mitochondria",
        explanation="Mitochondria produce ATP.",
        difficulty=QuizDifficulty.MEDIUM,
    )
    free_text_q = Question(
        quiz_id=quiz.id,
        position=1,
        question_type=QuestionType.SHORT_ANSWER,
        prompt="Explain photosynthesis.",
        reference_answer="Plants convert light into chemical energy.",
        explanation="Photosynthesis converts light energy to chemical energy.",
        difficulty=QuizDifficulty.MEDIUM,
    )
    db.add_all([objective_q, free_text_q])
    await db.flush()

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        status=QuizAttemptStatus.GRADING,
        time_limit_seconds=None,
        question_order=[str(objective_q.id), str(free_text_q.id)],
        answers={},
        submitted_at=datetime.now(UTC),
    )
    db.add(attempt)
    await db.flush()

    objective_answer = QuizAttemptAnswer(
        attempt_id=attempt.id,
        question_id=objective_q.id,
        student_answer="Mitochondria" if objective_is_correct else "Nucleus",
        is_correct=objective_is_correct,
        score=Decimal("1") if objective_is_correct else Decimal("0"),
        ai_feedback=None,
        # Milestone 7 gap (ADR 0011 #3): objective-type questions have no topic_tag
        # source at generation time -- confirmed still true below.
        topic_tag=None,
    )
    free_text_answer = QuizAttemptAnswer(
        attempt_id=attempt.id,
        question_id=free_text_q.id,
        student_answer="Plants use sunlight to make food.",
        is_correct=None,
        score=Decimal("0"),
        ai_feedback=None,
        topic_tag=None,
    )
    db.add_all([objective_answer, free_text_answer])
    await db.commit()
    await db.refresh(attempt)
    return attempt, objective_q, free_text_q


def _grade_result_json(question_id: uuid.UUID, *, score: float, is_correct: bool) -> str:
    return json.dumps(
        [
            {
                "question_id": str(question_id),
                "score": score,
                "is_correct": is_correct,
                "feedback": "Mostly right, missed the light-dependent reactions detail.",
                "topic_tag": "photosynthesis",
            }
        ]
    )


async def test_grade_quiz_attempt_persists_scores_and_rolls_up_attempt_score(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "grade-worker@example.com")
    attempt, objective_q, free_text_q = await _attempt_with_answers(
        db_session, user, notebook, objective_is_correct=True
    )
    response = AIResponse(
        task_type=TaskType.QUIZ_GRADING,
        provider=ProviderName.GEMINI,
        content=_grade_result_json(free_text_q.id, score=0.75, is_correct=True),
    )

    with (
        patch("app.workers.quiz_grading_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_grading_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _grade_quiz_attempt(attempt.id)

    await db_session.refresh(attempt)
    assert attempt.status is QuizAttemptStatus.GRADED
    assert attempt.graded_at is not None
    # objective row (score=1) + free-text row (score=0.75) = 1.75 / 2 questions.
    assert attempt.score == Decimal("1.75")
    assert attempt.max_score == Decimal("2")

    rows = {
        str(row.question_id): row
        for row in await db_session.scalars(
            select(QuizAttemptAnswer).where(QuizAttemptAnswer.attempt_id == attempt.id)
        )
    }
    free_text_row = rows[str(free_text_q.id)]
    assert free_text_row.score == Decimal("0.75")
    assert free_text_row.is_correct is True
    assert free_text_row.ai_feedback == "Mostly right, missed the light-dependent reactions detail."
    assert free_text_row.topic_tag == "photosynthesis"

    # Objective rows are untouched by this task -- already finalized by submit_attempt.
    objective_row = rows[str(objective_q.id)]
    assert objective_row.is_correct is True
    assert objective_row.score == Decimal("1")


async def test_grade_quiz_attempt_upserts_weak_topics_only_for_misses_with_topic_tag(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "grade-weak-topics@example.com")
    attempt, objective_q, free_text_q = await _attempt_with_answers(
        db_session, user, notebook, objective_is_correct=False
    )
    # Pre-existing weak topic for the same (user, notebook, topic) -- should increment,
    # not be replaced/overwritten.
    existing = WeakTopic(
        user_id=user.id, notebook_id=notebook.id, topic="photosynthesis", missed_count=2
    )
    db_session.add(existing)
    await db_session.commit()

    response = AIResponse(
        task_type=TaskType.QUIZ_GRADING,
        provider=ProviderName.GEMINI,
        content=_grade_result_json(free_text_q.id, score=0.2, is_correct=False),
    )

    with (
        patch("app.workers.quiz_grading_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_grading_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _grade_quiz_attempt(attempt.id)

    # `existing` was loaded (and committed) through `db_session` before the grading task
    # updated it via a separate session -- refresh so `db_session`'s identity map doesn't
    # serve the stale pre-grading value back.
    await db_session.refresh(existing)
    weak_topics = list(
        await db_session.scalars(
            select(WeakTopic).where(
                WeakTopic.user_id == user.id, WeakTopic.notebook_id == notebook.id
            )
        )
    )
    # Only one WeakTopic row: the free-text miss increments the existing "photosynthesis"
    # row. The objective-type miss has no topic_tag (Milestone 7 gap, ADR 0011 #3 --
    # confirmed still true: objective Questions carry no topic metadata at generation
    # time), so it contributes nothing to the aggregation despite being a miss.
    assert len(weak_topics) == 1
    assert weak_topics[0].topic == "photosynthesis"
    assert weak_topics[0].missed_count == 3  # 2 existing + 1 from this attempt
    assert weak_topics[0].last_detected_at is not None


async def test_grade_quiz_attempt_creates_new_weak_topic_when_none_exists(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "grade-new-weak-topic@example.com")
    attempt, _objective_q, free_text_q = await _attempt_with_answers(
        db_session, user, notebook, objective_is_correct=True
    )
    response = AIResponse(
        task_type=TaskType.QUIZ_GRADING,
        provider=ProviderName.GEMINI,
        content=_grade_result_json(free_text_q.id, score=0.1, is_correct=False),
    )

    with (
        patch("app.workers.quiz_grading_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_grading_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _grade_quiz_attempt(attempt.id)

    weak_topics = list(
        await db_session.scalars(
            select(WeakTopic).where(
                WeakTopic.user_id == user.id, WeakTopic.notebook_id == notebook.id
            )
        )
    )
    assert len(weak_topics) == 1
    assert weak_topics[0].topic == "photosynthesis"
    assert weak_topics[0].missed_count == 1


async def test_grade_quiz_attempt_failure_resets_status_to_submitted(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "grade-failure@example.com")
    attempt, objective_q, free_text_q = await _attempt_with_answers(
        db_session, user, notebook, objective_is_correct=True
    )

    with (
        patch("app.workers.quiz_grading_tasks.celery_session_maker", TestSessionLocal),
        patch(
            "app.workers.quiz_grading_tasks.run_task",
            new=AsyncMock(side_effect=OrchestrationError("QUIZ_GRADING failed: quota exhausted")),
        ),
    ):
        await _grade_quiz_attempt(attempt.id)

    await db_session.refresh(attempt)
    # Retryable -- not stuck in GRADING, not marked GRADED with an incomplete grade.
    assert attempt.status is QuizAttemptStatus.SUBMITTED
    assert attempt.score is None
    assert attempt.max_score is None
    assert attempt.graded_at is None

    # The free-text row is untouched (still pending) so a retry has something to grade.
    free_text_row = await db_session.scalar(
        select(QuizAttemptAnswer).where(
            QuizAttemptAnswer.attempt_id == attempt.id,
            QuizAttemptAnswer.question_id == free_text_q.id,
        )
    )
    assert free_text_row is not None
    assert free_text_row.is_correct is None
    assert free_text_row.score == Decimal("0")

    # No weak topics created from a failed grading run.
    weak_topics = list(
        await db_session.scalars(
            select(WeakTopic).where(
                WeakTopic.user_id == user.id, WeakTopic.notebook_id == notebook.id
            )
        )
    )
    assert weak_topics == []


async def test_grade_quiz_attempt_is_idempotent_when_not_in_grading_status(
    db_session: AsyncSession,
) -> None:
    """A duplicate/re-queued task delivery for an attempt that's already been graded (or
    isn't in a gradeable state) must be a no-op -- re-running would double-count
    weak-topic misses."""
    user, notebook = await _user_notebook(db_session, "grade-idempotent@example.com")
    attempt, _objective_q, _free_text_q = await _attempt_with_answers(
        db_session, user, notebook, objective_is_correct=True
    )
    attempt.status = QuizAttemptStatus.GRADED
    attempt.score = Decimal("2")
    attempt.max_score = Decimal("2")
    await db_session.commit()

    with (
        patch("app.workers.quiz_grading_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_grading_tasks.run_task", new=AsyncMock()) as run_task,
    ):
        await _grade_quiz_attempt(attempt.id)

    run_task.assert_not_awaited()
    await db_session.refresh(attempt)
    assert attempt.score == Decimal("2")


async def test_grade_quiz_attempt_returns_early_for_missing_attempt(
    db_session: AsyncSession,
) -> None:
    missing_id = uuid.uuid4()
    with (
        patch("app.workers.quiz_grading_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_grading_tasks.run_task", new=AsyncMock()) as run_task,
    ):
        await _grade_quiz_attempt(missing_id)
    run_task.assert_not_awaited()

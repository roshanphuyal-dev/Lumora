"""Tests for `app.services.quiz_attempt_service` -- the quiz-taking lifecycle
(start/autosave/submit/get) plus the deterministic half of grading dispatch.

The `get_attempt` answer-key boundary (SECURITY BOUNDARY comment in
`quiz_attempt_service.get_attempt`) is the most sensitive surface in this milestone --
see `test_get_attempt_never_leaks_answer_key_before_graded_and_reveals_after_grading`
below, which is written as an explicit, standalone regression test for exactly that
boundary and is exercised through the real HTTP response path (not just the service
return value), since that's what an actual client receives.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook
from app.models.quiz import Question, QuestionType, Quiz, QuizDifficulty, QuizStatus
from app.models.quiz_attempt import QuizAttempt, QuizAttemptAnswer, QuizAttemptStatus
from app.models.user import User
from app.services import quiz_attempt_service

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


async def _register(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-1", "full_name": "Test User"},
    )
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correct-horse-1"}
    )
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


async def _quiz(
    db: AsyncSession,
    user: User,
    notebook: Notebook,
    *,
    status: QuizStatus = QuizStatus.DONE,
    time_limit_seconds: int | None = None,
) -> Quiz:
    quiz = Quiz(
        notebook_id=notebook.id,
        user_id=user.id,
        title="Cell Biology",
        question_types=["mcq"],
        question_count=0,
        difficulty=QuizDifficulty.MEDIUM,
        status=status,
        time_limit_seconds=time_limit_seconds,
    )
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    return quiz


def _question(
    quiz_id: uuid.UUID,
    position: int,
    question_type: QuestionType,
    *,
    prompt: str = "Question?",
    type_data: dict | None = None,
    correct_answer: dict | list | str | None = None,
    reference_answer: str | None = None,
    explanation: str = "Explanation.",
    citation: dict | None = None,
    difficulty: QuizDifficulty = QuizDifficulty.MEDIUM,
) -> Question:
    return Question(
        quiz_id=quiz_id,
        position=position,
        question_type=question_type,
        prompt=prompt,
        type_data=type_data or {},
        correct_answer=correct_answer,
        reference_answer=reference_answer,
        explanation=explanation,
        citation=citation,
        difficulty=difficulty,
    )


async def _add_questions(db: AsyncSession, *questions: Question) -> list[Question]:
    db.add_all(questions)
    await db.commit()
    for question in questions:
        await db.refresh(question)
    return list(questions)


# ---------------------------------------------------------------------------
# start_attempt
# ---------------------------------------------------------------------------


async def test_start_attempt_rejects_quiz_not_done(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "start-not-done@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.GENERATING)
    await _add_questions(db_session, _question(quiz.id, 0, QuestionType.MCQ, correct_answer="A"))

    with pytest.raises(HTTPException) as exc_info:
        await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)
    assert exc_info.value.status_code == 409


async def test_start_attempt_rejects_quiz_with_no_questions(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "start-no-questions@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE)

    with pytest.raises(HTTPException) as exc_info:
        await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)
    assert exc_info.value.status_code == 409


async def test_start_attempt_snapshots_time_limit_and_shuffles_order(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "start-ok@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE, time_limit_seconds=600)
    questions = await _add_questions(
        db_session,
        _question(quiz.id, 0, QuestionType.MCQ, correct_answer="A"),
        _question(quiz.id, 1, QuestionType.MCQ, correct_answer="B"),
    )

    attempt = await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)

    assert attempt.status is QuizAttemptStatus.IN_PROGRESS
    assert attempt.time_limit_seconds == 600
    assert set(attempt.question_order) == {str(q.id) for q in questions}
    assert attempt.answers == {}


# ---------------------------------------------------------------------------
# autosave_answer
# ---------------------------------------------------------------------------


async def test_autosave_answer_rejects_non_owner(db_session: AsyncSession) -> None:
    owner, notebook = await _user_notebook(db_session, "autosave-owner@example.com")
    intruder, _ = await _user_notebook(db_session, "autosave-intruder@example.com")
    quiz = await _quiz(db_session, owner, notebook, status=QuizStatus.DONE)
    (question,) = await _add_questions(
        db_session, _question(quiz.id, 0, QuestionType.MCQ, correct_answer="A")
    )
    attempt = await quiz_attempt_service.start_attempt(db_session, owner.id, notebook.id, quiz.id)

    with pytest.raises(HTTPException) as exc_info:
        await quiz_attempt_service.autosave_answer(
            db_session, intruder.id, notebook.id, quiz.id, attempt.id, question.id, "A"
        )
    assert exc_info.value.status_code == 404


async def test_autosave_answer_rejects_when_not_in_progress(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "autosave-not-in-progress@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE)
    (question,) = await _add_questions(
        db_session, _question(quiz.id, 0, QuestionType.MCQ, correct_answer="A")
    )
    attempt = await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)
    attempt.status = QuizAttemptStatus.SUBMITTED
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await quiz_attempt_service.autosave_answer(
            db_session, user.id, notebook.id, quiz.id, attempt.id, question.id, "A"
        )
    assert exc_info.value.status_code == 409


async def test_autosave_answer_rejects_unknown_question(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "autosave-unknown-question@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE)
    await _add_questions(db_session, _question(quiz.id, 0, QuestionType.MCQ, correct_answer="A"))
    attempt = await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)

    with pytest.raises(HTTPException) as exc_info:
        await quiz_attempt_service.autosave_answer(
            db_session, user.id, notebook.id, quiz.id, attempt.id, uuid.uuid4(), "A"
        )
    assert exc_info.value.status_code == 404


async def test_autosave_answer_rejects_past_time_limit(db_session: AsyncSession) -> None:
    """Past-deadline autosave is REJECTED, not auto-submitted (design note in
    `quiz_attempt_service.autosave_answer`)."""
    user, notebook = await _user_notebook(db_session, "autosave-time-limit@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE, time_limit_seconds=1)
    (question,) = await _add_questions(
        db_session, _question(quiz.id, 0, QuestionType.MCQ, correct_answer="A")
    )
    attempt = await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)
    # Simulate time having passed well beyond the 1-second limit.
    attempt.started_at = datetime.now(UTC) - timedelta(seconds=100)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await quiz_attempt_service.autosave_answer(
            db_session, user.id, notebook.id, quiz.id, attempt.id, question.id, "A"
        )
    assert exc_info.value.status_code == 409
    assert "Time limit exceeded" in exc_info.value.detail


async def test_autosave_answer_persists_answer(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "autosave-persists@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE)
    (question,) = await _add_questions(
        db_session, _question(quiz.id, 0, QuestionType.MCQ, correct_answer="A")
    )
    attempt = await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)

    updated = await quiz_attempt_service.autosave_answer(
        db_session, user.id, notebook.id, quiz.id, attempt.id, question.id, "A"
    )
    assert updated.answers == {str(question.id): "A"}


# ---------------------------------------------------------------------------
# submit_attempt
# ---------------------------------------------------------------------------


async def test_submit_attempt_all_objective_grades_synchronously_and_skips_celery(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "submit-objective@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE)
    correct_q, wrong_q = await _add_questions(
        db_session,
        _question(quiz.id, 0, QuestionType.MCQ, correct_answer="Paris"),
        _question(quiz.id, 1, QuestionType.TRUE_FALSE, correct_answer="true"),
    )
    attempt = await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)
    await quiz_attempt_service.autosave_answer(
        db_session, user.id, notebook.id, quiz.id, attempt.id, correct_q.id, "Paris"
    )
    await quiz_attempt_service.autosave_answer(
        db_session, user.id, notebook.id, quiz.id, attempt.id, wrong_q.id, "false"
    )

    with patch("app.services.quiz_attempt_service.grade_quiz_attempt_task.delay") as delay:
        submitted = await quiz_attempt_service.submit_attempt(
            db_session, user.id, notebook.id, quiz.id, attempt.id
        )
    delay.assert_not_called()

    assert submitted.status is QuizAttemptStatus.GRADED
    assert submitted.graded_at is not None
    assert submitted.score == Decimal("1")
    assert submitted.max_score == Decimal("2")

    answer_rows = await db_session.scalars(
        select(QuizAttemptAnswer).where(QuizAttemptAnswer.attempt_id == submitted.id)
    )
    rows = {str(row.question_id): row for row in answer_rows}
    assert rows[str(correct_q.id)].is_correct is True
    assert rows[str(correct_q.id)].score == Decimal("1")
    assert rows[str(wrong_q.id)].is_correct is False
    assert rows[str(wrong_q.id)].score == Decimal("0")


async def test_submit_attempt_with_free_text_dispatches_grading_task(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "submit-free-text@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE)
    mcq_q, essay_q = await _add_questions(
        db_session,
        _question(quiz.id, 0, QuestionType.MCQ, correct_answer="Paris"),
        _question(
            quiz.id,
            1,
            QuestionType.SHORT_ANSWER,
            reference_answer="The mitochondria is the powerhouse of the cell.",
        ),
    )
    attempt = await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)
    await quiz_attempt_service.autosave_answer(
        db_session, user.id, notebook.id, quiz.id, attempt.id, mcq_q.id, "Paris"
    )
    await quiz_attempt_service.autosave_answer(
        db_session, user.id, notebook.id, quiz.id, attempt.id, essay_q.id, "It makes energy."
    )

    with patch("app.services.quiz_attempt_service.grade_quiz_attempt_task.delay") as delay:
        submitted = await quiz_attempt_service.submit_attempt(
            db_session, user.id, notebook.id, quiz.id, attempt.id
        )
    delay.assert_called_once_with(str(attempt.id))

    assert submitted.status is QuizAttemptStatus.GRADING
    assert submitted.score is None
    assert submitted.max_score is None

    answer_rows = await db_session.scalars(
        select(QuizAttemptAnswer).where(QuizAttemptAnswer.attempt_id == submitted.id)
    )
    rows = {str(row.question_id): row for row in answer_rows}
    assert rows[str(mcq_q.id)].is_correct is True
    assert rows[str(essay_q.id)].is_correct is None
    assert rows[str(essay_q.id)].score == Decimal("0")


async def test_submit_attempt_rejects_when_already_submitted(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "submit-twice@example.com")
    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE)
    await _add_questions(db_session, _question(quiz.id, 0, QuestionType.MCQ, correct_answer="A"))
    attempt = await quiz_attempt_service.start_attempt(db_session, user.id, notebook.id, quiz.id)
    with patch("app.services.quiz_attempt_service.grade_quiz_attempt_task.delay"):
        await quiz_attempt_service.submit_attempt(
            db_session, user.id, notebook.id, quiz.id, attempt.id
        )

    with pytest.raises(HTTPException) as exc_info:
        await quiz_attempt_service.submit_attempt(
            db_session, user.id, notebook.id, quiz.id, attempt.id
        )
    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# get_attempt -- SECURITY-CRITICAL: the answer-key boundary
# ---------------------------------------------------------------------------

_SECRET_CORRECT_ANSWER = "SECRET_CORRECT_ANSWER_MITOCHONDRIA"
_SECRET_REFERENCE_ANSWER = "SECRET_REFERENCE_ANSWER_ATP_SYNTHASE"
_SECRET_EXPLANATION = "SECRET_EXPLANATION_BECAUSE_OF_KREBS_CYCLE"
_SECRET_CITATION_SOURCE = "SECRET_CITATION_SOURCE_ID_42"


async def test_get_attempt_never_leaks_answer_key_before_graded_and_reveals_after_grading(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The answer key (`correct_answer`/`reference_answer`/`explanation`/`citation`) must
    never appear anywhere in the serialized attempt response while `status` is
    `in_progress`/`submitted`/`grading` -- not as a top-level field, not nested, not under
    any alternate key -- and must appear once `status == graded`.

    This is exercised through the real HTTP response body (not the Python return value),
    since that's the actual boundary a student's browser receives, and checked via a raw
    substring search over the full response text so no future refactor of the response
    shape can accidentally reintroduce a leak through a field this test didn't anticipate.
    """
    token = await _register(client, "leak-check@example.com")
    user = await db_session.scalar(select(User).where(User.email == "leak-check@example.com"))
    assert user is not None
    notebook = Notebook(owner_id=user.id, name="Biochem")
    db_session.add(notebook)
    await db_session.commit()
    await db_session.refresh(notebook)

    quiz = await _quiz(db_session, user, notebook, status=QuizStatus.DONE)
    mcq_q, essay_q = await _add_questions(
        db_session,
        _question(
            quiz.id,
            0,
            QuestionType.MCQ,
            correct_answer=_SECRET_CORRECT_ANSWER,
            explanation=_SECRET_EXPLANATION,
            citation={"source_id": _SECRET_CITATION_SOURCE, "chunk_id": None, "excerpt": None},
        ),
        _question(
            quiz.id,
            1,
            QuestionType.SHORT_ANSWER,
            reference_answer=_SECRET_REFERENCE_ANSWER,
            explanation=_SECRET_EXPLANATION,
        ),
    )

    base_url = f"/api/v1/notebooks/{notebook.id}/quizzes/{quiz.id}/attempts"

    # 1) in_progress
    start_resp = await client.post(base_url, headers=_auth(token))
    assert start_resp.status_code == 201
    attempt_id = start_resp.json()["id"]
    for secret in (
        _SECRET_CORRECT_ANSWER,
        _SECRET_REFERENCE_ANSWER,
        _SECRET_EXPLANATION,
        _SECRET_CITATION_SOURCE,
    ):
        assert secret not in start_resp.text

    get_resp = await client.get(f"{base_url}/{attempt_id}", headers=_auth(token))
    assert get_resp.json()["status"] == "in_progress"
    for secret in (
        _SECRET_CORRECT_ANSWER,
        _SECRET_REFERENCE_ANSWER,
        _SECRET_EXPLANATION,
        _SECRET_CITATION_SOURCE,
    ):
        assert secret not in get_resp.text

    # Answer both questions so submit has something to grade.
    await client.patch(
        f"{base_url}/{attempt_id}",
        json={"question_id": str(mcq_q.id), "answer": "guess"},
        headers=_auth(token),
    )
    await client.patch(
        f"{base_url}/{attempt_id}",
        json={"question_id": str(essay_q.id), "answer": "my essay answer"},
        headers=_auth(token),
    )

    # 2) submitted -> grading (has a free-text question, so Celery dispatch is mocked out
    # and the attempt lands in GRADING, not GRADED).
    with patch("app.services.quiz_attempt_service.grade_quiz_attempt_task.delay"):
        submit_resp = await client.post(f"{base_url}/{attempt_id}/submit", headers=_auth(token))
    assert submit_resp.json()["status"] == "grading"
    for secret in (
        _SECRET_CORRECT_ANSWER,
        _SECRET_REFERENCE_ANSWER,
        _SECRET_EXPLANATION,
        _SECRET_CITATION_SOURCE,
    ):
        assert secret not in submit_resp.text

    grading_get_resp = await client.get(f"{base_url}/{attempt_id}", headers=_auth(token))
    assert grading_get_resp.json()["status"] == "grading"
    for secret in (
        _SECRET_CORRECT_ANSWER,
        _SECRET_REFERENCE_ANSWER,
        _SECRET_EXPLANATION,
        _SECRET_CITATION_SOURCE,
    ):
        assert secret not in grading_get_resp.text

    # 3) Finalize grading directly (bypassing the Celery task, which is covered by its own
    # test file) so we can assert the post-GRADED reveal.
    attempt = await db_session.get(QuizAttempt, uuid.UUID(attempt_id))
    assert attempt is not None
    pending_rows = await db_session.scalars(
        select(QuizAttemptAnswer).where(
            QuizAttemptAnswer.attempt_id == attempt.id, QuizAttemptAnswer.is_correct.is_(None)
        )
    )
    for row in pending_rows:
        row.is_correct = True
        row.score = Decimal("1")
        row.ai_feedback = "Good answer."
        row.topic_tag = "cell-biology"
    attempt.status = QuizAttemptStatus.GRADED
    attempt.graded_at = datetime.now(UTC)
    attempt.score = Decimal("2")
    attempt.max_score = Decimal("2")
    await db_session.commit()

    graded_resp = await client.get(f"{base_url}/{attempt_id}", headers=_auth(token))
    assert graded_resp.json()["status"] == "graded"
    for secret in (
        _SECRET_CORRECT_ANSWER,
        _SECRET_REFERENCE_ANSWER,
        _SECRET_EXPLANATION,
        _SECRET_CITATION_SOURCE,
    ):
        assert secret in graded_resp.text

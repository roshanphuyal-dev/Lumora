"""Quiz-taking backend: attempt lifecycle (start/autosave/submit/read) plus the
deterministic half of grading (ADR 0011). AI-graded free-text questions are dispatched to
`app.workers.quiz_grading_tasks.grade_quiz_attempt_task`, not handled here.

All functions take a `user_id` and scope every query to it, same pattern as
`quiz_service.py`/`notebook_service.py`.
"""

import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.quiz import Question, QuestionType, Quiz, QuizStatus
from app.models.quiz_attempt import QuizAttempt, QuizAttemptAnswer, QuizAttemptStatus
from app.schemas.course import PageResult
from app.schemas.quiz import QuestionRead, QuestionReviewRead
from app.schemas.quiz_attempt import (
    QuestionWithReview,
    QuizAttemptAnswerReview,
    QuizAttemptRead,
    QuizAttemptReviewRead,
)
from app.services.learning_service import record_attempt_evidence, record_quiz_completed_activity
from app.services.quiz_service import get_owned_quiz
from app.workers.quiz_grading_tasks import grade_quiz_attempt_task

_FREE_TEXT_TYPES = {
    QuestionType.SHORT_ANSWER,
    QuestionType.LONG_ANSWER,
    QuestionType.CASE_STUDY,
}
# mcq/true_false/fill_blank/matching/assertion_reason -- everything not in
# _FREE_TEXT_TYPES is graded deterministically (ADR 0011).


def _normalize(value: object) -> str:
    """Loose-equality normalization for deterministic grading -- trims incidental
    whitespace/case differences from typed/selected answers without pretending to do any
    semantic matching (that's what QUIZ_GRADING is for)."""
    return str(value).strip().casefold()


def _grade_objective(question: Question, student_answer: object) -> bool:
    """Exact-match grading for mcq/true_false/fill_blank/matching/assertion_reason --
    1.0/0.0 only, no partial credit (ADR 0011). Returns False for any shape mismatch
    (missing/malformed answer) rather than raising -- an unanswered/garbled question is
    simply wrong, not a server error.
    """
    correct = question.correct_answer
    if student_answer is None or correct is None:
        return False

    if question.question_type in {
        QuestionType.MCQ,
        QuestionType.TRUE_FALSE,
        QuestionType.ASSERTION_REASON,
    }:
        if not isinstance(student_answer, str) or not isinstance(correct, str):
            return False
        return _normalize(student_answer) == _normalize(correct)

    if question.question_type == QuestionType.FILL_BLANK:
        if isinstance(correct, list):
            if not isinstance(student_answer, list) or len(student_answer) != len(correct):
                return False
            return all(
                _normalize(given) == _normalize(expected)
                for given, expected in zip(student_answer, correct, strict=True)
            )
        if isinstance(correct, str) and isinstance(student_answer, str):
            return _normalize(student_answer) == _normalize(correct)
        return False

    if question.question_type == QuestionType.MATCHING:
        if not isinstance(correct, list) or not isinstance(student_answer, list):
            return False
        try:
            expected_pairs = {(_normalize(p["left"]), _normalize(p["right"])) for p in correct}
            given_pairs = {(_normalize(p["left"]), _normalize(p["right"])) for p in student_answer}
        except (KeyError, TypeError):
            return False
        return expected_pairs == given_pairs

    return False  # pragma: no cover -- free-text types never reach here


def _time_limit_exceeded(attempt: QuizAttempt) -> bool:
    if attempt.time_limit_seconds is None:
        return False
    deadline = attempt.started_at + timedelta(seconds=attempt.time_limit_seconds)
    return datetime.now(UTC) >= deadline


async def _get_owned_quiz_and_attempt(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
) -> tuple[Quiz, QuizAttempt]:
    """Ownership-scoped (quiz, attempt) lookup shared by every attempt endpoint except
    `start_attempt`. Reuses `get_owned_quiz` for the notebook/quiz ownership chain (same
    pattern every other service in this codebase chains through), then scopes the attempt
    to that quiz + the same user -- `QuizAttempt` has no `notebook_id` column of its own.
    """
    quiz = await get_owned_quiz(db, user_id, notebook_id, quiz_id)
    attempt = await db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.id == attempt_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user_id,
        )
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz attempt not found")
    return quiz, attempt


def _questions_in_order(quiz: Quiz, question_order: list[str]) -> list[Question]:
    by_id = {str(question.id): question for question in quiz.questions}
    return [by_id[qid] for qid in question_order if qid in by_id]


async def start_attempt(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, quiz_id: uuid.UUID
) -> QuizAttempt:
    """Multiple concurrent/repeat attempts per quiz are allowed -- simplest model given
    `QuizAttempt` has no uniqueness constraint on (quiz_id, user_id); each attempt is
    independent (own `question_order`/`answers`/score).
    """
    quiz = await get_owned_quiz(db, user_id, notebook_id, quiz_id)
    if quiz.status != QuizStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quiz is not ready to attempt yet",
        )
    if not quiz.questions:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quiz has no questions")

    question_order = [str(question.id) for question in quiz.questions]
    random.shuffle(question_order)

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user_id,
        status=QuizAttemptStatus.IN_PROGRESS,
        time_limit_seconds=quiz.time_limit_seconds,
        question_order=question_order,
        answers={},
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt


async def autosave_answer(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    question_id: uuid.UUID,
    answer: dict | list | str,
) -> QuizAttempt:
    """Time-limit handling: REJECT, not auto-submit.

    Once `now > started_at + time_limit_seconds`, further autosave writes are rejected
    (409) rather than silently triggering a full submit as a side effect. Autosave is a
    lightweight, frequently-called (debounced) write path; submit is not (it runs
    deterministic grading for every objective question and, for free-text quizzes,
    dispatches the Celery grading task and flips status). Folding submit's side effects
    into a stray post-deadline autosave call would make an innocuous-looking PATCH
    responsible for finalizing a grade -- surprising and hard to reason about. The client
    is expected to treat this 409 (or its own deadline tracking) as the signal to call
    `POST .../submit` itself, which performs the real transition exactly once.

    Note `submit_attempt` does NOT re-check the deadline -- a still-`in_progress` attempt
    past its clock is still submittable with whatever was saved; the alternative (a client
    that missed the exact deadline losing all progress) is worse than accepting a
    slightly-late submit.
    """
    quiz, attempt = await _get_owned_quiz_and_attempt(db, user_id, notebook_id, quiz_id, attempt_id)
    if attempt.status != QuizAttemptStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt is not in progress"
        )
    if str(question_id) not in attempt.question_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question does not belong to this attempt"
        )
    if _time_limit_exceeded(attempt):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time limit exceeded for this attempt -- submit to finalize.",
        )

    # Reassign (not in-place mutate) so SQLAlchemy detects the JSONB column change.
    answers = dict(attempt.answers)
    answers[str(question_id)] = answer
    attempt.answers = answers
    await db.commit()
    await db.refresh(attempt)
    return attempt


async def submit_attempt(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
) -> QuizAttempt:
    quiz, attempt = await _get_owned_quiz_and_attempt(db, user_id, notebook_id, quiz_id, attempt_id)
    if attempt.status != QuizAttemptStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt already submitted"
        )

    questions = _questions_in_order(quiz, attempt.question_order)
    has_free_text = False
    answer_rows: list[QuizAttemptAnswer] = []
    for question in questions:
        raw_answer = attempt.answers.get(str(question.id))
        student_answer = raw_answer if raw_answer is not None else ""
        if question.question_type in _FREE_TEXT_TYPES:
            has_free_text = True
            answer_rows.append(
                QuizAttemptAnswer(
                    attempt_id=attempt.id,
                    question=question,
                    student_answer=student_answer,
                    is_correct=None,
                    score=Decimal("0"),
                    ai_feedback=None,
                    topic_tag=None,
                )
            )
        else:
            is_correct = _grade_objective(question, raw_answer)
            answer_rows.append(
                QuizAttemptAnswer(
                    attempt_id=attempt.id,
                    question=question,
                    student_answer=student_answer,
                    is_correct=is_correct,
                    score=Decimal("1") if is_correct else Decimal("0"),
                    ai_feedback=None,
                    topic_tag=question.topic,
                )
            )

    db.add_all(answer_rows)
    now = datetime.now(UTC)
    attempt.submitted_at = now

    if has_free_text:
        # Free-text grading happens asynchronously (ADR 0011) -- the submit request
        # returns immediately once objective answers are recorded and the free-text rows
        # are staged (score=0/is_correct=None until the Celery task fills them in).
        attempt.status = QuizAttemptStatus.GRADING
        await db.commit()
        grade_quiz_attempt_task.delay(str(attempt.id))
    else:
        # No free-text questions -- skip the Celery round-trip entirely (matches
        # QUIZ_GRADING's own empty-items short-circuit) and finalize synchronously.
        attempt.status = QuizAttemptStatus.GRADED
        attempt.graded_at = now
        attempt.score = sum((row.score for row in answer_rows), Decimal("0"))
        attempt.max_score = Decimal(len(answer_rows))
        if get_settings().personalization_enabled:
            await record_attempt_evidence(
                db, attempt, quiz.notebook_id, answer_rows, observed_at=now
            )
            await record_quiz_completed_activity(db, attempt, quiz.notebook_id, occurred_at=now)
        await db.commit()

    await db.refresh(attempt)
    return attempt


async def get_attempt(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
) -> QuizAttemptRead | QuizAttemptReviewRead:
    quiz, attempt = await _get_owned_quiz_and_attempt(db, user_id, notebook_id, quiz_id, attempt_id)

    # SECURITY BOUNDARY: a student polling this endpoint while the attempt is
    # in_progress/submitted/grading must NEVER receive an answer key
    # (correct_answer/reference_answer/explanation/citation), not even nested in a debug
    # field. We enforce this structurally, not by field-filtering a shared shape: below
    # this `if`, the response is built exclusively from `QuestionRead` (Milestone 3's
    # answer-key-free schema -- those fields don't exist on it, so there is nothing to
    # accidentally serialize). Only past this branch, once `status == GRADED`, do we
    # switch to `QuestionReviewRead`/`QuizAttemptReviewRead`, which do carry the answer
    # key. Do not add a "reveal early" flag/param to this function -- that would collapse
    # the boundary for any caller able to set it.
    if attempt.status != QuizAttemptStatus.GRADED:
        questions = _questions_in_order(quiz, attempt.question_order)
        return QuizAttemptRead(
            id=attempt.id,
            quiz_id=attempt.quiz_id,
            status=attempt.status,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            time_limit_seconds=attempt.time_limit_seconds,
            question_order=[uuid.UUID(qid) for qid in attempt.question_order],
            answers=attempt.answers,
            questions=[QuestionRead.model_validate(question) for question in questions],
            created_at=attempt.created_at,
            updated_at=attempt.updated_at,
        )

    answer_rows = await db.scalars(
        select(QuizAttemptAnswer).where(QuizAttemptAnswer.attempt_id == attempt.id)
    )
    answers_by_question = {str(row.question_id): row for row in answer_rows}
    questions_by_id = {str(question.id): question for question in quiz.questions}
    review_questions = []
    for question_id in attempt.question_order:
        question = questions_by_id.get(question_id)
        answer = answers_by_question.get(question_id)
        if question is None or answer is None:
            continue
        review_questions.append(
            QuestionWithReview(
                question=QuestionReviewRead.model_validate(question),
                answer=QuizAttemptAnswerReview.model_validate(answer),
            )
        )

    return QuizAttemptReviewRead(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        status=attempt.status,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        graded_at=attempt.graded_at,
        time_limit_seconds=attempt.time_limit_seconds,
        score=attempt.score,
        max_score=attempt.max_score,
        questions=review_questions,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
    )


async def list_attempts(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    quiz_id: uuid.UUID,
    limit: int,
    offset: int,
) -> PageResult[QuizAttempt]:
    await get_owned_quiz(db, user_id, notebook_id, quiz_id)
    filters = [QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id]
    total = await db.scalar(select(func.count()).select_from(QuizAttempt).where(*filters))
    result = await db.scalars(
        select(QuizAttempt)
        .where(*filters)
        .order_by(QuizAttempt.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)

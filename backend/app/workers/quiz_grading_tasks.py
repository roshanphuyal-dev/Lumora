"""Async free-text grading for a submitted `QuizAttempt` (Milestone 7, ADR 0011).

Deterministic (objective-type) grading happens synchronously in
`app.services.quiz_attempt_service.submit_attempt` -- this task only handles the
short_answer/long_answer/case_study rows that service left with `score=0`/`is_correct=None`
as placeholders, via one batched `TaskType.QUIZ_GRADING` call.

Retry expectations: no automatic Celery retry (`bind=True`/`self.retry`) is wired up here,
matching every other generation task in this codebase (`quiz_tasks.py`, `note_tasks.py`,
`flashcard_tasks.py`, `studio_tasks.py` -- none auto-retry on provider failure). On failure
the attempt is left in `QuizAttemptStatus.SUBMITTED` (not stuck in `GRADING` forever) with
its `QuizAttemptAnswer` rows already persisted -- nothing needs to be redone except the AI
call and the status flip, so re-dispatching `grade_quiz_attempt_task.delay(str(attempt_id))`
(from an ops script, or a future manual "retry grading" endpoint -- out of scope here) picks
up exactly where this left off.
"""

import asyncio
import logging
import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal

from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import GradingItem, QuestionGradeResult, QuizGradingRequest
from ai.orchestrator.task_types import TaskType
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.session import celery_session_maker
from app.models.quiz_attempt import QuizAttempt, QuizAttemptAnswer, QuizAttemptStatus
from app.models.weak_topic import WeakTopic
from app.services.learning_service import record_attempt_evidence, record_quiz_completed_activity
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
_GRADE_RESULTS = TypeAdapter(list[QuestionGradeResult])


@celery_app.task(name="quizzes.grade_attempt")
def grade_quiz_attempt_task(attempt_id: str) -> None:
    asyncio.run(_grade_quiz_attempt(uuid.UUID(attempt_id)))


async def _upsert_weak_topics(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, topics: list[str]
) -> None:
    """Increment `weak_topics.missed_count` for every distinct missed topic (ADR 0011) --
    a running tally across attempts, not a per-attempt snapshot.
    """
    now = datetime.now(UTC)
    for topic, count in Counter(topics).items():
        weak_topic = await db.scalar(
            select(WeakTopic).where(
                WeakTopic.user_id == user_id,
                WeakTopic.notebook_id == notebook_id,
                WeakTopic.topic == topic,
            )
        )
        if weak_topic is None:
            db.add(
                WeakTopic(
                    user_id=user_id,
                    notebook_id=notebook_id,
                    topic=topic,
                    missed_count=count,
                    last_detected_at=now,
                )
            )
        else:
            weak_topic.missed_count += count
            weak_topic.last_detected_at = now


async def _grade_quiz_attempt(attempt_id: uuid.UUID) -> None:
    async with celery_session_maker() as db:
        attempt = await db.scalar(
            select(QuizAttempt)
            .options(
                selectinload(QuizAttempt.attempt_answers).selectinload(QuizAttemptAnswer.question),
                selectinload(QuizAttempt.quiz),
            )
            .where(QuizAttempt.id == attempt_id)
        )
        if attempt is None:
            return
        if attempt.status != QuizAttemptStatus.GRADING:
            # Not in a gradeable state (already graded, or a duplicate/re-queued task
            # delivery) -- returning here is what keeps this idempotent; re-running the
            # grading call and re-incrementing weak_topics for an already-graded attempt
            # would double-count misses.
            return

        pending_rows = [row for row in attempt.attempt_answers if row.is_correct is None]
        # Objective rows always have is_correct set (True/False) by submit_attempt, so this
        # filter can only select the free-text rows staged for AI grading.

        try:
            if pending_rows:
                items = [
                    GradingItem(
                        question_id=str(row.question_id),
                        question_type=row.question.question_type.value,
                        prompt=row.question.prompt,
                        reference_answer=row.question.reference_answer or "",
                        student_answer=(
                            row.student_answer
                            if isinstance(row.student_answer, str)
                            else str(row.student_answer)
                        ),
                    )
                    for row in pending_rows
                ]
                response = await run_task(TaskType.QUIZ_GRADING, QuizGradingRequest(items=items))
                results = _GRADE_RESULTS.validate_json(response.content)
                results_by_question = {result.question_id: result for result in results}
                rows_by_question = {str(row.question_id): row for row in pending_rows}
                for question_id, result in results_by_question.items():
                    row = rows_by_question.get(question_id)
                    if row is None:
                        continue
                    row.score = Decimal(str(result.score))
                    row.is_correct = result.is_correct
                    row.ai_feedback = result.feedback
                    row.topic_tag = result.topic_tag
        except (OrchestrationError, ValidationError):
            logger.exception("Failed to grade quiz attempt %s", attempt_id)
            attempt.status = QuizAttemptStatus.SUBMITTED
            await db.commit()
            return

        attempt.score = sum((row.score for row in attempt.attempt_answers), Decimal("0"))
        attempt.max_score = Decimal(len(attempt.attempt_answers))
        attempt.status = QuizAttemptStatus.GRADED
        attempt.graded_at = datetime.now(UTC)

        missed_topics = [
            row.topic_tag
            for row in attempt.attempt_answers
            if row.is_correct is False and row.topic_tag
        ]
        if missed_topics:
            await _upsert_weak_topics(db, attempt.user_id, attempt.quiz.notebook_id, missed_topics)

        if get_settings().personalization_enabled:
            await record_attempt_evidence(
                db,
                attempt,
                attempt.quiz.notebook_id,
                list(attempt.attempt_answers),
                observed_at=attempt.graded_at,
            )
            await record_quiz_completed_activity(
                db,
                attempt,
                attempt.quiz.notebook_id,
                occurred_at=attempt.graded_at,
            )

        await db.commit()

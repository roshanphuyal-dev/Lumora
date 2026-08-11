"""Tests for `app.workers.quiz_tasks.generate_quiz_task` (`_generate_quiz`).

Only the orchestrator's `run_task` is mocked (the actual Gemini/NotebookLM calls) --
persistence, status transitions, and the per-question-type `type_data`/`correct_answer`/
`reference_answer` split (`_question_kwargs`) run for real, same pattern as
`tests/test_flashcards.py::test_generate_flashcards_persists_ordered_cards`.
"""

import json
import uuid
from unittest.mock import AsyncMock, patch

from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import AIResponse, ProviderName
from ai.orchestrator.task_types import TaskType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook
from app.models.quiz import Question, Quiz, QuizDifficulty, QuizStatus
from app.models.user import User
from app.workers.quiz_tasks import _generate_quiz
from tests.conftest import TestSessionLocal


async def _user_notebook_quiz(db: AsyncSession, email: str) -> tuple[Notebook, Quiz]:
    user = User(email=email, full_name="Test User")
    db.add(user)
    await db.flush()
    notebook = Notebook(owner_id=user.id, name="Biology")
    db.add(notebook)
    await db.flush()
    quiz = Quiz(
        notebook_id=notebook.id,
        user_id=user.id,
        title="Cell Biology",
        topic="Cells",
        question_types=["mcq", "matching", "fill_blank", "case_study"],
        question_count=4,
        difficulty=QuizDifficulty.MIXED,
    )
    db.add(quiz)
    await db.commit()
    await db.refresh(notebook)
    await db.refresh(quiz)
    return notebook, quiz


def _mixed_items_json() -> str:
    return json.dumps(
        [
            {
                "question_type": "mcq",
                "prompt": "What is the powerhouse of the cell?",
                "options": ["Nucleus", "Mitochondria", "Ribosome"],
                "correct_answer": "Mitochondria",
                "difficulty": "easy",
                "explanation": "Mitochondria produce ATP.",
                "citation": {"source_id": "src-1"},
            },
            {
                "question_type": "matching",
                "prompt": "Match the organelle to its function.",
                "pairs": [
                    {"left": "Nucleus", "right": "Stores DNA"},
                    {"left": "Ribosome", "right": "Synthesizes protein"},
                ],
                "correct_answer": "Nucleus=Stores DNA, Ribosome=Synthesizes protein",
                "difficulty": "medium",
                "explanation": "Organelles have distinct roles.",
            },
            {
                "question_type": "fill_blank",
                "prompt": "The _____ controls the cell.",
                "blanks": ["nucleus"],
                "correct_answer": "nucleus",
                "difficulty": "easy",
                "explanation": "The nucleus is the control center.",
            },
            {
                "question_type": "case_study",
                "prompt": "Why did the cell fail to divide?",
                "scenario": "A cell is exposed to a spindle-fiber inhibitor.",
                "reference_answer": "Spindle fibers can't form, blocking mitosis.",
                "difficulty": "hard",
                "explanation": "Spindle inhibitors block mitosis.",
            },
        ]
    )


async def test_generate_quiz_persists_ordered_questions_and_status_done(
    db_session: AsyncSession,
) -> None:
    notebook, quiz = await _user_notebook_quiz(db_session, "quiz-worker@example.com")
    response = AIResponse(
        task_type=TaskType.QUIZ_GENERATION,
        provider=ProviderName.GEMINI,
        content=_mixed_items_json(),
    )

    with (
        patch("app.workers.quiz_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _generate_quiz(quiz.id)

    await db_session.refresh(quiz)
    assert quiz.status is QuizStatus.DONE
    assert quiz.error_message is None

    questions = list(
        await db_session.scalars(
            select(Question).where(Question.quiz_id == quiz.id).order_by(Question.position)
        )
    )
    assert [q.position for q in questions] == [0, 1, 2, 3]
    assert [q.question_type.value for q in questions] == [
        "mcq",
        "matching",
        "fill_blank",
        "case_study",
    ]

    mcq = questions[0]
    assert mcq.type_data == {"options": ["Nucleus", "Mitochondria", "Ribosome"]}
    assert mcq.correct_answer == "Mitochondria"
    assert mcq.citation == {"source_id": "src-1", "chunk_id": None, "excerpt": None}

    matching = questions[1]
    # The correct pairing must live only in `correct_answer` -- `type_data` (shown by the
    # answer-key-free QuestionRead schema) must not leak the pairing itself.
    assert matching.type_data == {
        "left": ["Nucleus", "Ribosome"],
        "right": ["Stores DNA", "Synthesizes protein"],
    }
    assert matching.correct_answer == [
        {"left": "Nucleus", "right": "Stores DNA"},
        {"left": "Ribosome", "right": "Synthesizes protein"},
    ]

    fill_blank = questions[2]
    assert fill_blank.correct_answer == ["nucleus"]

    case_study = questions[3]
    assert case_study.type_data == {"scenario": "A cell is exposed to a spindle-fiber inhibitor."}
    assert case_study.correct_answer is None
    assert case_study.reference_answer == "Spindle fibers can't form, blocking mitosis."


async def test_generate_quiz_status_transitions_pending_generating_done(
    db_session: AsyncSession,
) -> None:
    notebook, quiz = await _user_notebook_quiz(db_session, "quiz-transitions@example.com")
    assert quiz.status is QuizStatus.PENDING

    observed_status_during_call: list[QuizStatus] = []

    async def _capture_status_then_respond(*_args: object, **_kwargs: object) -> AIResponse:
        async with TestSessionLocal() as probe_session:
            probe_quiz = await probe_session.get(Quiz, quiz.id)
            assert probe_quiz is not None
            observed_status_during_call.append(probe_quiz.status)
        return AIResponse(
            task_type=TaskType.QUIZ_GENERATION,
            provider=ProviderName.GEMINI,
            content="[]",
        )

    with (
        patch("app.workers.quiz_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_tasks.run_task", side_effect=_capture_status_then_respond),
    ):
        await _generate_quiz(quiz.id)

    # The status was committed to GENERATING before the AI call happened...
    assert observed_status_during_call == [QuizStatus.GENERATING]
    # ...and flipped to DONE once the call succeeded (empty question list is valid).
    await db_session.refresh(quiz)
    assert quiz.status is QuizStatus.DONE


async def test_generate_quiz_persists_failure_on_orchestration_error(
    db_session: AsyncSession,
) -> None:
    notebook, quiz = await _user_notebook_quiz(db_session, "quiz-failure@example.com")

    with (
        patch("app.workers.quiz_tasks.celery_session_maker", TestSessionLocal),
        patch(
            "app.workers.quiz_tasks.run_task",
            new=AsyncMock(side_effect=OrchestrationError("QUIZ_GENERATION failed: no quota")),
        ),
    ):
        await _generate_quiz(quiz.id)

    await db_session.refresh(quiz)
    assert quiz.status is QuizStatus.FAILED
    assert quiz.error_message == "QUIZ_GENERATION failed: no quota"
    questions = list(await db_session.scalars(select(Question).where(Question.quiz_id == quiz.id)))
    assert questions == []


async def test_generate_quiz_persists_failure_on_malformed_response(
    db_session: AsyncSession,
) -> None:
    """A response that fails `QuestionItem` validation (e.g. malformed JSON) must fail the
    quiz cleanly, not raise out of the task or leave partial rows."""
    notebook, quiz = await _user_notebook_quiz(db_session, "quiz-malformed@example.com")
    response = AIResponse(
        task_type=TaskType.QUIZ_GENERATION,
        provider=ProviderName.GEMINI,
        content="not valid json",
    )

    with (
        patch("app.workers.quiz_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _generate_quiz(quiz.id)

    await db_session.refresh(quiz)
    assert quiz.status is QuizStatus.FAILED
    assert quiz.error_message is not None
    questions = list(await db_session.scalars(select(Question).where(Question.quiz_id == quiz.id)))
    assert questions == []


async def test_generate_quiz_returns_early_for_missing_quiz(db_session: AsyncSession) -> None:
    """No matching `Quiz` row (e.g. deleted between dispatch and worker pickup) -- the
    task should just return, not raise."""
    missing_id = uuid.uuid4()
    with (
        patch("app.workers.quiz_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.quiz_tasks.run_task", new=AsyncMock()) as run_task,
    ):
        await _generate_quiz(missing_id)
    run_task.assert_not_awaited()

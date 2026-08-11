import asyncio
import json
import logging
import uuid

from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import (
    Citation,
    NotebookQueryRequest,
    QuestionItem,
    QuizGenerationRequest,
)
from ai.orchestrator.task_types import TaskType
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import celery_session_maker
from app.models.notebook import Notebook, NotebookSourceIndexStatus
from app.models.quiz import Question, QuestionType, Quiz, QuizDifficulty, QuizStatus
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
_QUESTION_ITEMS = TypeAdapter(list[QuestionItem])


@celery_app.task(name="quizzes.generate")
def generate_quiz_task(quiz_id: str) -> None:
    asyncio.run(_generate_quiz(uuid.UUID(quiz_id)))


def _question_kwargs(item: QuestionItem) -> dict:
    """Split a generated `QuestionItem` into the non-answer `type_data` shown while a
    quiz is being taken (`QuestionRead`) vs. the answer-key columns (`correct_answer`/
    `reference_answer`) only ever exposed via `QuestionReviewRead` post-grading.

    `matching` needs special care: `QuestionItem.pairs` *is* the correct correspondence,
    so it can't be stored verbatim in `type_data` (that would leak the answer to the
    pre-attempt endpoint) -- the left/right terms go in `type_data` unpaired, and the
    correct pairing goes in `correct_answer`.
    """
    question_type = item.question_type
    type_data: dict = {}
    correct_answer: dict | list | str | None = None
    reference_answer: str | None = None

    if question_type == "mcq":
        type_data = {"options": item.options or []}
        correct_answer = item.correct_answer
    elif question_type == "true_false":
        correct_answer = item.correct_answer
    elif question_type == "fill_blank":
        correct_answer = item.blanks or item.correct_answer
    elif question_type == "matching":
        pairs = item.pairs or []
        type_data = {
            "left": [pair.left for pair in pairs],
            "right": [pair.right for pair in pairs],
        }
        correct_answer = [pair.model_dump() for pair in pairs]
    elif question_type == "case_study":
        type_data = {"scenario": item.scenario}
        reference_answer = item.reference_answer
    else:  # short_answer / long_answer
        reference_answer = item.reference_answer

    return {
        "type_data": type_data,
        "correct_answer": correct_answer,
        "reference_answer": reference_answer,
    }


async def _generate_quiz(quiz_id: uuid.UUID) -> None:
    async with celery_session_maker() as db:
        quiz = await db.get(Quiz, quiz_id)
        if quiz is None:
            return
        quiz.status = QuizStatus.GENERATING
        quiz.error_message = None
        await db.commit()

        try:
            notebook = await db.scalar(
                select(Notebook)
                .options(selectinload(Notebook.sources))
                .where(Notebook.id == quiz.notebook_id)
            )
            context = ""
            citations: list[Citation] = []
            query = quiz.topic or quiz.title
            if (
                notebook is not None
                and notebook.notebooklm_notebook_id
                and any(
                    source.indexing_status == NotebookSourceIndexStatus.INDEXED
                    for source in notebook.sources
                )
            ):
                try:
                    retrieval = await run_task(
                        TaskType.NOTEBOOK_QUERY,
                        NotebookQueryRequest(
                            notebooklm_notebook_id=notebook.notebooklm_notebook_id,
                            question=query,
                        ),
                    )
                except OrchestrationError:
                    pass
                else:
                    context = retrieval.content
                    citations = retrieval.citations

            response = await run_task(
                TaskType.QUIZ_GENERATION,
                QuizGenerationRequest(
                    topic=query,
                    context=context,
                    citations=citations,
                    question_types=quiz.question_types,
                    count=quiz.question_count,
                    difficulty=quiz.difficulty.value,
                ),
            )
            items = _QUESTION_ITEMS.validate_python(json.loads(response.content))
            questions = [
                Question(
                    quiz_id=quiz.id,
                    position=position,
                    question_type=QuestionType(item.question_type),
                    prompt=item.prompt,
                    difficulty=QuizDifficulty(item.difficulty),
                    explanation=item.explanation or "",
                    citation=item.citation.model_dump() if item.citation else None,
                    **_question_kwargs(item),
                )
                for position, item in enumerate(items)
            ]
        except (OrchestrationError, ValidationError, ValueError, TypeError) as exc:
            logger.exception("Failed to generate quiz %s", quiz_id)
            quiz.status = QuizStatus.FAILED
            quiz.error_message = str(exc)
            await db.commit()
            return

        db.add_all(questions)
        quiz.status = QuizStatus.DONE
        await db.commit()

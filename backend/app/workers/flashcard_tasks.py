import asyncio
import json
import logging
import uuid

from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import (
    Citation,
    FlashcardGenerationRequest,
    FlashcardItem,
    NotebookQueryRequest,
)
from ai.orchestrator.task_types import TaskType
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import celery_session_maker
from app.models.flashcard import Flashcard, FlashcardSet, FlashcardSetStatus
from app.models.notebook import Notebook, NotebookSourceIndexStatus
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
_FLASHCARD_ITEMS = TypeAdapter(list[FlashcardItem])


@celery_app.task(name="flashcards.generate")
def generate_flashcards_task(flashcard_set_id: str, topic: str = "", count: int = 12) -> None:
    asyncio.run(_generate_flashcards(uuid.UUID(flashcard_set_id), topic=topic, count=count))


async def _generate_flashcards(
    flashcard_set_id: uuid.UUID, *, topic: str = "", count: int = 12
) -> None:
    async with celery_session_maker() as db:
        flashcard_set = await db.get(FlashcardSet, flashcard_set_id)
        if flashcard_set is None:
            return
        flashcard_set.status = FlashcardSetStatus.GENERATING
        flashcard_set.error_message = None
        await db.commit()

        try:
            notebook = await db.scalar(
                select(Notebook)
                .options(selectinload(Notebook.sources))
                .where(Notebook.id == flashcard_set.notebook_id)
            )
            context = ""
            citations: list[Citation] = []
            query = topic or flashcard_set.title
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
                TaskType.FLASHCARD_GENERATION,
                FlashcardGenerationRequest(
                    topic=query, context=context, citations=citations, count=count
                ),
            )
            items = _FLASHCARD_ITEMS.validate_python(json.loads(response.content))
        except (OrchestrationError, ValidationError, ValueError, TypeError) as exc:
            logger.exception("Failed to generate flashcard set %s", flashcard_set_id)
            flashcard_set.status = FlashcardSetStatus.FAILED
            flashcard_set.error_message = str(exc)
            await db.commit()
            return

        db.add_all(
            [
                Flashcard(
                    flashcard_set_id=flashcard_set.id,
                    position=position,
                    front=item.front,
                    back=item.back,
                    citation=item.citation.model_dump() if item.citation else None,
                )
                for position, item in enumerate(items)
            ]
        )
        flashcard_set.status = FlashcardSetStatus.DONE
        await db.commit()

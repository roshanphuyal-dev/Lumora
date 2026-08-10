import asyncio
import json
import logging
import uuid

from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import (
    Citation,
    NotebookQueryRequest,
    NotesGenerationRequest,
    StructuredNoteGenerationRequest,
)
from ai.orchestrator.task_types import TaskType
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import celery_session_maker
from app.models.note import Note, NoteMaterialType, NoteStatus
from app.models.notebook import Notebook, NotebookSourceIndexStatus
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="notes.generate")
def generate_note_task(note_id: str, topic: str = "") -> None:
    asyncio.run(_generate_note(uuid.UUID(note_id), topic=topic))


async def _generate_note(note_id: uuid.UUID, *, topic: str = "") -> None:
    async with celery_session_maker() as db:
        note = await db.get(Note, note_id)
        if note is None:
            return
        note.status = NoteStatus.GENERATING
        note.error_message = None
        await db.commit()

        try:
            notebook = await db.scalar(
                select(Notebook)
                .options(selectinload(Notebook.sources))
                .where(Notebook.id == note.notebook_id)
            )
            context = ""
            citations: list[Citation] = []
            query = topic or note.title
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

            if note.material_type in {
                NoteMaterialType.NOTE,
                NoteMaterialType.STUDY_GUIDE,
                NoteMaterialType.CHEAT_SHEET,
                NoteMaterialType.FORMULA_SHEET,
            }:
                response = await run_task(
                    TaskType.NOTES_GENERATION,
                    NotesGenerationRequest(
                        material_type=note.material_type.value,
                        topic=query,
                        context=context,
                        citations=citations,
                    ),
                )
                note.content = response.content
            else:
                response = await run_task(
                    TaskType.STRUCTURED_NOTE_GENERATION,
                    StructuredNoteGenerationRequest(
                        material_type=note.material_type.value,
                        topic=query,
                        context=context,
                        citations=citations,
                    ),
                )
                note.content_json = json.loads(response.content)
        except (OrchestrationError, json.JSONDecodeError) as exc:
            logger.exception("Failed to generate note %s", note_id)
            note.status = NoteStatus.FAILED
            note.error_message = str(exc)
            await db.commit()
            return

        note.citations = [citation.model_dump() for citation in response.citations]
        note.status = NoteStatus.DONE
        await db.commit()

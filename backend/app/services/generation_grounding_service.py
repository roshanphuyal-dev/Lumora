import logging
import uuid

from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import Citation, NotebookQueryRequest
from ai.orchestrator.task_types import TaskType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.notebook import Notebook, NotebookSourceIndexStatus
from app.services import rag_retrieval_service

logger = logging.getLogger(__name__)


async def get_generation_grounding(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    query: str,
) -> tuple[str, list[Citation]]:
    """Resolve NotebookLM-first grounding for generated study materials."""
    notebook = await db.scalar(
        select(Notebook)
        .options(selectinload(Notebook.sources))
        .where(Notebook.id == notebook_id, Notebook.owner_id == user_id)
    )
    context = ""
    citations: list[Citation] = []
    notebooklm_adequate = False
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
            logger.warning(
                "NotebookLM grounding failed for notebook %s", notebook_id, exc_info=True
            )
        else:
            notebooklm_adequate = bool(retrieval.content.strip() and retrieval.citations)
            if notebooklm_adequate:
                context = retrieval.content
                citations = retrieval.citations

    if get_settings().rag_enabled and not notebooklm_adequate:
        try:
            local = await rag_retrieval_service.retrieve(db, user_id, notebook_id, query)
        except (OrchestrationError, rag_retrieval_service.LocalRetrievalError):
            logger.warning("Local grounding failed for notebook %s", notebook_id, exc_info=True)
        else:
            context = local.context
            citations = local.citations

    return context, citations

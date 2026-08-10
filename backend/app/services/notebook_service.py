"""Notebook/NotebookSource persistence for the Notebook API and its indexing worker.

All functions except the ones in the "worker-only" section at the bottom take
a `user_id`/`owner_id` and scope every query to it — see `document_service.py`
for the pattern this mirrors (worker-only lookups keyed by id alone, called
only on ids the backend itself already checked ownership for).
"""

import logging
import uuid

from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import Citation, NotebookQueryRequest, TeachingExplanationRequest
from ai.orchestrator.task_types import TaskType
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentParseStatus
from app.models.notebook import Notebook, NotebookSource, NotebookSourceIndexStatus
from app.schemas.course import PageResult

logger = logging.getLogger(__name__)


async def create_notebook(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    name: str,
    description: str | None = None,
    subject_id: uuid.UUID | None = None,
) -> Notebook:
    notebook = Notebook(
        owner_id=owner_id, subject_id=subject_id, name=name, description=description
    )
    db.add(notebook)
    await db.commit()
    await db.refresh(notebook)
    return notebook


async def list_notebooks(
    db: AsyncSession,
    owner_id: uuid.UUID,
    limit: int,
    offset: int,
    *,
    search: str | None = None,
) -> PageResult[Notebook]:
    filters = [Notebook.owner_id == owner_id]
    if search:
        filters.append(
            or_(
                Notebook.name.icontains(search, autoescape=True),
                Notebook.description.icontains(search, autoescape=True),
            )
        )

    total = await db.scalar(select(func.count()).select_from(Notebook).where(*filters))
    result = await db.scalars(
        select(Notebook)
        .where(*filters)
        .order_by(Notebook.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)


async def get_owned_notebook(
    db: AsyncSession, owner_id: uuid.UUID, notebook_id: uuid.UUID
) -> Notebook:
    """Fetches the notebook with `sources` eager-loaded (avoids an async lazy-load
    on the `sources` relationship when serializing `NotebookDetail`).
    """
    notebook = await db.scalar(
        select(Notebook)
        .options(selectinload(Notebook.sources))
        .where(Notebook.id == notebook_id, Notebook.owner_id == owner_id)
    )
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


async def delete_notebook(db: AsyncSession, owner_id: uuid.UUID, notebook_id: uuid.UUID) -> None:
    notebook = await get_owned_notebook(db, owner_id, notebook_id)
    await db.delete(notebook)
    await db.commit()


async def ask_question(
    db: AsyncSession, owner_id: uuid.UUID, notebook_id: uuid.UUID, question: str
) -> tuple[str, str, list[Citation]]:
    """Ask a teaching-explanation question, grounded in the notebook's sources when possible.

    If the notebook has at least one `indexed` source, retrieves a grounded answer +
    citations from NotebookLM first (`TaskType.NOTEBOOK_QUERY`,
    `docs/AI.md#routing-logic` step 1) and hands it to Gemini as `context` for teaching
    framing (`docs/AI_WORKFLOWS.md#4`). A notebook with no indexed sources yet (or a failed
    NotebookLM retrieval — logged, not raised) falls back to the previous plain/ungrounded
    call rather than failing the whole request over a missing/degraded knowledge base.
    """
    notebook = await get_owned_notebook(db, owner_id, notebook_id)

    context = ""
    citations: list[Citation] = []
    has_indexed_source = any(
        source.indexing_status == NotebookSourceIndexStatus.INDEXED for source in notebook.sources
    )
    if notebook.notebooklm_notebook_id and has_indexed_source:
        try:
            retrieval = await run_task(
                TaskType.NOTEBOOK_QUERY,
                NotebookQueryRequest(
                    notebooklm_notebook_id=notebook.notebooklm_notebook_id, question=question
                ),
            )
        except OrchestrationError:
            logger.warning(
                "NotebookLM retrieval failed for notebook %s; falling back to an ungrounded answer",
                notebook_id,
                exc_info=True,
            )
        else:
            context = retrieval.content
            citations = retrieval.citations

    try:
        response = await run_task(
            TaskType.TEACHING_EXPLANATION,
            TeachingExplanationRequest(question=question, context=context, citations=citations),
        )
    except OrchestrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Couldn't get an answer right now: {exc}",
        ) from exc

    return response.content, response.provider.value, response.citations


async def attach_source(
    db: AsyncSession, owner_id: uuid.UUID, notebook_id: uuid.UUID, document_id: uuid.UUID
) -> NotebookSource:
    """Create a `pending` NotebookSource row.

    Does NOT dispatch the indexing task — the caller (the attach-source route)
    does that once this returns, to avoid a circular import between this
    module and `app/workers/notebook_tasks.py` (which itself imports this
    module). Requires the document to have finished parsing (`parse_status ==
    done`) since NotebookLM indexing needs `Document.extracted_text` — see
    `ai/orchestrator/schemas.py:DocumentIndexRequest`.
    """
    notebook = await get_owned_notebook(db, owner_id, notebook_id)

    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.uploaded_by == owner_id)
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.parse_status != DocumentParseStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document has not finished parsing yet",
        )

    existing = await db.scalar(
        select(NotebookSource).where(
            NotebookSource.notebook_id == notebook.id,
            NotebookSource.document_id == document.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already a source of this notebook",
        )

    source = NotebookSource(
        notebook_id=notebook.id,
        document_id=document.id,
        indexing_status=NotebookSourceIndexStatus.PENDING,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def get_owned_source(
    db: AsyncSession, owner_id: uuid.UUID, notebook_id: uuid.UUID, source_id: uuid.UUID
) -> NotebookSource:
    source = await db.scalar(
        select(NotebookSource)
        .join(Notebook, Notebook.id == NotebookSource.notebook_id)
        .where(
            NotebookSource.id == source_id,
            NotebookSource.notebook_id == notebook_id,
            Notebook.owner_id == owner_id,
        )
    )
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


async def detach_source(
    db: AsyncSession, owner_id: uuid.UUID, notebook_id: uuid.UUID, source_id: uuid.UUID
) -> None:
    source = await get_owned_source(db, owner_id, notebook_id, source_id)
    await db.delete(source)
    await db.commit()


# --- Worker-only: called from app/workers/notebook_tasks.py on ids the backend
# --- itself already checked ownership for at attach time, not on a
# --- client-supplied id from an inbound request. -----------------------------


async def get_source(db: AsyncSession, source_id: uuid.UUID) -> NotebookSource:
    source = await db.get(NotebookSource, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


async def get_notebook(db: AsyncSession, notebook_id: uuid.UUID) -> Notebook:
    notebook = await db.get(Notebook, notebook_id)
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


async def mark_source_indexed(db: AsyncSession, source_id: uuid.UUID) -> NotebookSource:
    source = await get_source(db, source_id)
    source.indexing_status = NotebookSourceIndexStatus.INDEXED
    await db.commit()
    await db.refresh(source)
    return source


async def mark_source_index_failed(db: AsyncSession, source_id: uuid.UUID) -> NotebookSource:
    source = await get_source(db, source_id)
    source.indexing_status = NotebookSourceIndexStatus.FAILED
    await db.commit()
    await db.refresh(source)
    return source

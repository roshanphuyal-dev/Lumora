import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.notebook import (
    NotebookAskRequest,
    NotebookAskResponse,
    NotebookCreate,
    NotebookDetail,
    NotebookImageSearchRequest,
    NotebookImageSearchResponse,
    NotebookRead,
    NotebookSearchRequest,
    NotebookSearchResponse,
    NotebookSourceCreate,
    NotebookSourceRead,
)
from app.services import notebook_service
from app.workers.notebook_tasks import index_notebook_source_task

router = APIRouter(prefix="/notebooks", tags=["notebooks"])

Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)


@router.post("", response_model=NotebookRead, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    payload: NotebookCreate, current_user: CurrentUser, db: DbSession
) -> NotebookRead:
    notebook = await notebook_service.create_notebook(
        db,
        current_user.id,
        name=payload.name,
        description=payload.description,
        subject_id=payload.subject_id,
    )
    return NotebookRead.model_validate(notebook)


@router.get("", response_model=Page[NotebookRead])
async def list_notebooks(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
    search: str | None = Query(default=None, min_length=1, max_length=255),
) -> Page[NotebookRead]:
    page = await notebook_service.list_notebooks(db, current_user.id, limit, offset, search=search)
    return Page[NotebookRead](
        items=[NotebookRead.model_validate(n) for n in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{notebook_id}", response_model=NotebookDetail)
async def get_notebook(
    notebook_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> NotebookDetail:
    notebook = await notebook_service.get_owned_notebook(db, current_user.id, notebook_id)
    return NotebookDetail.model_validate(notebook)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(notebook_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    await notebook_service.delete_notebook(db, current_user.id, notebook_id)


@router.post(
    "/{notebook_id}/sources",
    response_model=NotebookSourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def attach_source(
    notebook_id: uuid.UUID,
    payload: NotebookSourceCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> NotebookSourceRead:
    """Attach a Document as a Notebook source and start NotebookLM indexing.

    Requires the document to have finished parsing (`parse_status == done`) —
    NotebookLM indexing needs already-extracted text
    (`ai/orchestrator/schemas.py:DocumentIndexRequest`); returns 409 otherwise.
    Indexing requires a machine with `nlm` installed and `nlm login` already
    run (`docs/DEPLOYMENT.md`) — without that, the Celery task marks the
    source `failed` rather than `indexed`; see `app/workers/notebook_tasks.py`.
    """
    source = await notebook_service.attach_source(
        db, current_user.id, notebook_id, payload.document_id
    )
    index_notebook_source_task.delay(str(source.id))
    return NotebookSourceRead.model_validate(source)


@router.delete("/{notebook_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_source(
    notebook_id: uuid.UUID, source_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    await notebook_service.detach_source(db, current_user.id, notebook_id, source_id)


@router.post("/{notebook_id}/ask", response_model=NotebookAskResponse)
async def ask_notebook_question(
    notebook_id: uuid.UUID,
    payload: NotebookAskRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> NotebookAskResponse:
    """Ask a teaching-explanation question, grounded in the notebook's indexed sources
    when it has any (`docs/AI.md#routing-logic` step 1 -> step 2,
    `app/services/notebook_service.py:ask_question`); falls back to a plain Gemini/OpenCode
    Zen call (ADR 0008 fallback included) otherwise. 404s for a notebook the caller doesn't
    own.
    """
    content, provider, citations = await notebook_service.ask_question(
        db, current_user.id, notebook_id, payload.question
    )
    return NotebookAskResponse(content=content, provider=provider, citations=citations)


@router.post("/{notebook_id}/search", response_model=NotebookSearchResponse)
async def search_notebook_web(
    notebook_id: uuid.UUID,
    payload: NotebookSearchRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> NotebookSearchResponse:
    """Search the open internet for current/external information not covered by the
    notebook's indexed sources (`TaskType.INTERNET_SEARCH`, Tavily/Brave + Gemini
    synthesis, ADR 0012). 404s for a notebook the caller doesn't own.
    """
    content, provider, citations = await notebook_service.search_web(
        db, current_user.id, notebook_id, payload.query
    )
    return NotebookSearchResponse(content=content, provider=provider, citations=citations)


@router.post("/{notebook_id}/image-search", response_model=NotebookImageSearchResponse)
async def search_notebook_topic_image(
    notebook_id: uuid.UUID,
    payload: NotebookImageSearchRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> NotebookImageSearchResponse:
    """Look up a topic-relevant image (`TaskType.TOPIC_IMAGE_SEARCH`, Wikimedia primary,
    Openverse fallback, ADR 0010). `found=false` (all other fields `None`) means no usable
    image was found for this topic, a real outcome distinct from a request failure (502).
    404s for a notebook the caller doesn't own.
    """
    result = await notebook_service.search_topic_image(
        db, current_user.id, notebook_id, payload.query
    )
    if result is None:
        return NotebookImageSearchResponse(found=False)
    return NotebookImageSearchResponse(
        found=True,
        image_url=result.image_url,
        attribution=result.attribution,
        license=result.license,
        source_url=result.source_url,
    )

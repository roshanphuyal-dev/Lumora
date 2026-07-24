import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.notebook import (
    NotebookCreate,
    NotebookDetail,
    NotebookRead,
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
    current_user: CurrentUser, db: DbSession, limit: int = Limit, offset: int = Offset
) -> Page[NotebookRead]:
    page = await notebook_service.list_notebooks(db, current_user.id, limit, offset)
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
    Indexing itself won't currently resolve to `indexed` for real — see
    `app/workers/notebook_tasks.py`'s docstring for why (NotebookLM CLI/MCP
    integration is stubbed).
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

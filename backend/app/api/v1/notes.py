import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.note import NoteCreate, NoteRead
from app.services import note_service

router = APIRouter(prefix="/notebooks/{notebook_id}/notes", tags=["notes"])
Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    notebook_id: uuid.UUID, payload: NoteCreate, current_user: CurrentUser, db: DbSession
) -> NoteRead:
    note = await note_service.create_note(db, current_user.id, notebook_id, payload)
    return NoteRead.model_validate(note)


@router.get("", response_model=Page[NoteRead])
async def list_notes(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> Page[NoteRead]:
    page = await note_service.list_notes(db, current_user.id, notebook_id, limit, offset)
    return Page[NoteRead](
        items=[NoteRead.model_validate(note) for note in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    notebook_id: uuid.UUID, note_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> NoteRead:
    note = await note_service.get_owned_note(db, current_user.id, notebook_id, note_id)
    return NoteRead.model_validate(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    notebook_id: uuid.UUID, note_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    await note_service.delete_note(db, current_user.id, notebook_id, note_id)

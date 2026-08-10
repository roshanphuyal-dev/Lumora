import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note, NoteMaterialType, NoteStatus
from app.schemas.course import PageResult
from app.schemas.note import NoteCreate
from app.services.notebook_service import get_owned_notebook
from app.workers.note_tasks import generate_note_task


async def create_note(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, payload: NoteCreate
) -> Note:
    await get_owned_notebook(db, user_id, notebook_id)
    material_type = NoteMaterialType(payload.material_type)
    default_title = (
        "Untitled note" if material_type is NoteMaterialType.NOTE else "Untitled study guide"
    )
    note = Note(
        notebook_id=notebook_id,
        user_id=user_id,
        material_type=material_type,
        status=NoteStatus.PENDING,
        title=payload.title or payload.topic or default_title,
        content=None,
        citations=[],
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    generate_note_task.delay(str(note.id), payload.topic)
    return note


async def list_notes(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, limit: int, offset: int
) -> PageResult[Note]:
    await get_owned_notebook(db, user_id, notebook_id)
    filters = [Note.notebook_id == notebook_id, Note.user_id == user_id]
    total = await db.scalar(select(func.count()).select_from(Note).where(*filters))
    result = await db.scalars(
        select(Note).where(*filters).order_by(Note.created_at.desc()).limit(limit).offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)


async def get_owned_note(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, note_id: uuid.UUID
) -> Note:
    note = await db.scalar(
        select(Note).where(
            Note.id == note_id, Note.notebook_id == notebook_id, Note.user_id == user_id
        )
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


async def delete_note(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, note_id: uuid.UUID
) -> None:
    note = await get_owned_note(db, user_id, notebook_id, note_id)
    await db.delete(note)
    await db.commit()

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.flashcard import FlashcardSet, FlashcardSetStatus
from app.schemas.course import PageResult
from app.schemas.flashcard import FlashcardSetCreate
from app.services.notebook_service import get_owned_notebook
from app.workers.flashcard_tasks import generate_flashcards_task


async def create_flashcard_set(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    payload: FlashcardSetCreate,
) -> FlashcardSet:
    await get_owned_notebook(db, user_id, notebook_id)
    flashcard_set = FlashcardSet(
        notebook_id=notebook_id,
        user_id=user_id,
        status=FlashcardSetStatus.PENDING,
        title=payload.title or payload.topic or "Untitled flashcard set",
    )
    db.add(flashcard_set)
    await db.commit()
    await db.refresh(flashcard_set)
    generate_flashcards_task.delay(str(flashcard_set.id), payload.topic, payload.count)
    return await get_owned_flashcard_set(db, user_id, notebook_id, flashcard_set.id)


async def list_flashcard_sets(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, limit: int, offset: int
) -> PageResult[FlashcardSet]:
    await get_owned_notebook(db, user_id, notebook_id)
    filters = [FlashcardSet.notebook_id == notebook_id, FlashcardSet.user_id == user_id]
    total = await db.scalar(select(func.count()).select_from(FlashcardSet).where(*filters))
    result = await db.scalars(
        select(FlashcardSet)
        .options(selectinload(FlashcardSet.flashcards))
        .where(*filters)
        .order_by(FlashcardSet.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)


async def get_owned_flashcard_set(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, set_id: uuid.UUID
) -> FlashcardSet:
    flashcard_set = await db.scalar(
        select(FlashcardSet)
        .options(selectinload(FlashcardSet.flashcards))
        .where(
            FlashcardSet.id == set_id,
            FlashcardSet.notebook_id == notebook_id,
            FlashcardSet.user_id == user_id,
        )
    )
    if flashcard_set is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard set not found")
    return flashcard_set


async def delete_flashcard_set(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, set_id: uuid.UUID
) -> None:
    flashcard_set = await get_owned_flashcard_set(db, user_id, notebook_id, set_id)
    await db.delete(flashcard_set)
    await db.commit()

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.flashcard import FlashcardSetCreate, FlashcardSetRead
from app.services import flashcard_service

router = APIRouter(prefix="/notebooks/{notebook_id}/flashcard-sets", tags=["flashcards"])
Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)


@router.post("", response_model=FlashcardSetRead, status_code=status.HTTP_201_CREATED)
async def create_flashcard_set(
    notebook_id: uuid.UUID,
    payload: FlashcardSetCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> FlashcardSetRead:
    flashcard_set = await flashcard_service.create_flashcard_set(
        db, current_user.id, notebook_id, payload
    )
    return FlashcardSetRead.model_validate(flashcard_set)


@router.get("", response_model=Page[FlashcardSetRead])
async def list_flashcard_sets(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> Page[FlashcardSetRead]:
    page = await flashcard_service.list_flashcard_sets(
        db, current_user.id, notebook_id, limit, offset
    )
    return Page[FlashcardSetRead](
        items=[FlashcardSetRead.model_validate(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{set_id}", response_model=FlashcardSetRead)
async def get_flashcard_set(
    notebook_id: uuid.UUID, set_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> FlashcardSetRead:
    flashcard_set = await flashcard_service.get_owned_flashcard_set(
        db, current_user.id, notebook_id, set_id
    )
    return FlashcardSetRead.model_validate(flashcard_set)


@router.delete("/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flashcard_set(
    notebook_id: uuid.UUID, set_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    await flashcard_service.delete_flashcard_set(db, current_user.id, notebook_id, set_id)

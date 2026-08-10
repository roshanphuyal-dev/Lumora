import uuid
from datetime import datetime

from ai.orchestrator.schemas import Citation
from pydantic import BaseModel, ConfigDict, Field

from app.models.flashcard import FlashcardSetStatus


class FlashcardSetCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    topic: str = Field(default="", max_length=2000)
    count: int = Field(default=12, ge=1, le=100)


class FlashcardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    flashcard_set_id: uuid.UUID
    position: int
    front: str
    back: str
    citation: Citation | None
    created_at: datetime
    updated_at: datetime


class FlashcardSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notebook_id: uuid.UUID
    status: FlashcardSetStatus
    title: str
    error_message: str | None
    flashcards: list[FlashcardRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

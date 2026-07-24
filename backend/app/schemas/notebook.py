import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.notebook import NotebookSourceIndexStatus


class NotebookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    subject_id: uuid.UUID | None = None


class NotebookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID | None
    name: str
    description: str | None
    created_at: datetime


class NotebookSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    indexing_status: NotebookSourceIndexStatus
    created_at: datetime


class NotebookSourceCreate(BaseModel):
    document_id: uuid.UUID


class NotebookDetail(NotebookRead):
    sources: list[NotebookSourceRead] = Field(default_factory=list)

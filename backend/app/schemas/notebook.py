import uuid
from datetime import datetime

from ai.orchestrator.schemas import Citation
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


class NotebookAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class NotebookAskResponse(BaseModel):
    """`citations` is empty unless the notebook has an indexed source and NotebookLM
    retrieval succeeded (`app/services/notebook_service.py:ask_question`) -- an ungrounded
    answer (no sources yet, or a degraded NotebookLM call) legitimately has none.
    """

    content: str
    provider: str
    citations: list[Citation] = Field(default_factory=list)

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
    notebooklm_source_id: str | None = None
    created_at: datetime


class NotebookSourceCreate(BaseModel):
    document_id: uuid.UUID


class CitationChunkRead(BaseModel):
    source_id: uuid.UUID
    chunk_id: uuid.UUID
    source_title: str
    locator_kind: str | None = None
    locator: int | None = None
    text: str


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


class NotebookSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class NotebookSearchResponse(BaseModel):
    """Mirrors `NotebookAskResponse`'s shape -- `content` is Gemini's synthesized answer,
    `citations` always derived from the search results themselves
    (`ai/orchestrator/orchestrator.py:_run_internet_search`).
    """

    content: str
    provider: str
    citations: list[Citation] = Field(default_factory=list)


class NotebookPaperSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class NotebookPaperSearchResponse(BaseModel):
    """Mirrors `NotebookSearchResponse`'s shape (ADR 0013) -- `content` is Gemini's
    synthesized answer, `citations` always derived from the paper results themselves
    (`ai/orchestrator/orchestrator.py:_run_paper_search`).
    """

    content: str
    provider: str
    citations: list[Citation] = Field(default_factory=list)


class NotebookImageSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class NotebookImageSearchResponse(BaseModel):
    """`found` distinguishes "no usable image for this topic" (a real, expected outcome --
    `found=False`, every other field `None`) from a failed request (raises instead of
    returning a response at all -- see the route handler), mirroring
    `AIResponse.metadata["found"]` from
    `ai/orchestrator/orchestrator.py:_run_topic_image_search`. The frontend must branch on
    `found`, not on whether `image_url` happens to be empty.
    """

    found: bool
    image_url: str | None = None
    attribution: str | None = None
    license: str | None = None
    source_url: str | None = None

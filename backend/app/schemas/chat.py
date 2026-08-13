import uuid
from datetime import datetime

from ai.orchestrator.schemas import Citation
from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import MessageKind, MessageRole


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notebook_id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class WebSearchCreate(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class MessageImageCreate(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class MessageImageResult(BaseModel):
    image_url: str
    attribution: str
    license: str
    source_url: str


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    kind: MessageKind
    content: str
    provider: str | None
    citations: list[Citation] = Field(default_factory=list)
    image_result: MessageImageResult | None = None
    created_at: datetime


class WebSearchMessagePair(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead

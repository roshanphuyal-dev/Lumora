import uuid
from datetime import datetime
from typing import Literal

from ai.orchestrator.schemas import Citation
from pydantic import BaseModel, ConfigDict, Field

from app.models.note import NoteMaterialType, NoteStatus


class NoteCreate(BaseModel):
    material_type: Literal[
        "note",
        "study_guide",
        "cheat_sheet",
        "formula_sheet",
        "mnemonics",
        "timeline",
        "comparison_chart",
    ]
    title: str | None = Field(default=None, min_length=1, max_length=255)
    topic: str = Field(default="", max_length=2000)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notebook_id: uuid.UUID
    material_type: NoteMaterialType
    status: NoteStatus
    title: str
    content: str | None
    content_json: dict | list | None
    citations: list[Citation] = Field(default_factory=list)
    error_message: str | None
    created_at: datetime
    updated_at: datetime

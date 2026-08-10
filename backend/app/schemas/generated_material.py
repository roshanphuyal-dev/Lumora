import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.generated_material import MaterialArtifactType, MaterialStatus


class GeneratedMaterialCreate(BaseModel):
    artifact_type: Literal["audio", "report", "slides", "infographic", "mindmap", "data_table"]
    title: str | None = Field(default=None, min_length=1, max_length=255)
    format: str | None = None
    length: str | None = None
    focus: str | None = None
    language: str | None = None
    prompt: str | None = None
    orientation: str | None = None
    detail: str | None = None
    description: str | None = None


class GeneratedMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notebook_id: uuid.UUID
    artifact_type: MaterialArtifactType
    status: MaterialStatus
    title: str
    content: str | None
    error_message: str | None
    storage_path: str | None = Field(exclude=True)
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def has_download(self) -> bool:
        return self.storage_path is not None

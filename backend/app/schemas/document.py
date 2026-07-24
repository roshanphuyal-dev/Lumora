import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentParseStatus


class DocumentRead(BaseModel):
    """List-item shape — omits `extracted_text` to keep list responses light."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID | None
    filename: str
    mime_type: str
    file_type: str
    parse_status: DocumentParseStatus
    created_at: datetime


class DocumentDetail(DocumentRead):
    """Detail shape — also serves as the parse-status poll target (`extracted_text`
    is populated once `parse_status` reaches `done`).
    """

    extracted_text: str | None
    updated_at: datetime

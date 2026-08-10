import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.document import DocumentParseStatus


class DocumentRead(BaseModel):
    """List-item shape — omits `extracted_text` to keep list responses light."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID | None
    filename: str
    mime_type: str
    file_type: str
    source_url: str | None
    title: str | None
    description: str | None
    parse_status: DocumentParseStatus
    created_at: datetime


class DocumentDetail(DocumentRead):
    """Detail shape — also serves as the parse-status poll target (`extracted_text`
    is populated once `parse_status` reaches `done`).
    """

    extracted_text: str | None
    updated_at: datetime


class UrlDocumentCreate(BaseModel):
    """Body for `POST /documents/url` — a link resource, parsed by fetching the page
    instead of an uploaded file (see `app/parsers/url_parser.py`).
    """

    url: HttpUrl
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    subject_id: uuid.UUID | None = None

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentParseStatus
from app.models.user import User
from app.parsers.base import ParsedDocument
from app.services import document_service


async def _create_document(db_session: AsyncSession) -> Document:
    user = User(email=f"{uuid.uuid4().hex[:12]}@example.com", full_name="Test User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    document = Document(
        uploaded_by=user.id,
        filename="notes.pdf",
        storage_path="notes.pdf",
        mime_type="application/pdf",
        file_type="pdf",
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


async def test_get_document_raises_404_when_missing(db_session: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await document_service.get_document(db_session, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_mark_processing_updates_status(db_session: AsyncSession) -> None:
    document = await _create_document(db_session)

    updated = await document_service.mark_processing(db_session, document.id)

    assert updated.parse_status == DocumentParseStatus.PROCESSING


async def test_mark_parsed_sets_text_and_done_status(db_session: AsyncSession) -> None:
    document = await _create_document(db_session)

    updated = await document_service.mark_parsed(
        db_session, document.id, ParsedDocument(text="extracted text")
    )

    assert updated.parse_status == DocumentParseStatus.DONE
    assert updated.extracted_text == "extracted text"


async def test_mark_parse_failed_sets_failed_status(db_session: AsyncSession) -> None:
    document = await _create_document(db_session)

    updated = await document_service.mark_parse_failed(db_session, document.id)

    assert updated.parse_status == DocumentParseStatus.FAILED

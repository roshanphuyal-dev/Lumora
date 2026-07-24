import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentParseStatus
from app.models.user import User
from app.parsers.base import ParsedDocument
from app.workers.document_tasks import _parse_document
from tests.conftest import TestSessionLocal


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


async def test_parse_document_marks_done_on_success(db_session: AsyncSession) -> None:
    document = await _create_document(db_session)
    fake_storage = AsyncMock()
    fake_storage.download.return_value = b"%PDF-fake%"

    with (
        patch("app.workers.document_tasks.async_session_maker", TestSessionLocal),
        patch("app.workers.document_tasks.get_file_storage", return_value=fake_storage),
        patch(
            "app.workers.document_tasks.get_parser",
            return_value=lambda _bytes: ParsedDocument(text="extracted text", sections=[]),
        ),
    ):
        await _parse_document(document.id)

    await db_session.refresh(document)
    assert document.parse_status == DocumentParseStatus.DONE
    assert document.extracted_text == "extracted text"


async def test_parse_document_marks_failed_on_parser_error(db_session: AsyncSession) -> None:
    document = await _create_document(db_session)
    fake_storage = AsyncMock()
    fake_storage.download.return_value = b"not-a-real-file"

    def _boom(_bytes: bytes) -> ParsedDocument:
        raise ValueError("bad file")

    with (
        patch("app.workers.document_tasks.async_session_maker", TestSessionLocal),
        patch("app.workers.document_tasks.get_file_storage", return_value=fake_storage),
        patch("app.workers.document_tasks.get_parser", return_value=_boom),
    ):
        await _parse_document(document.id)

    await db_session.refresh(document)
    assert document.parse_status == DocumentParseStatus.FAILED


async def test_parse_document_marks_failed_when_file_missing(db_session: AsyncSession) -> None:
    document = await _create_document(db_session)
    fake_storage = AsyncMock()
    fake_storage.download.side_effect = FileNotFoundError("no such file")

    with (
        patch("app.workers.document_tasks.async_session_maker", TestSessionLocal),
        patch("app.workers.document_tasks.get_file_storage", return_value=fake_storage),
    ):
        await _parse_document(document.id)

    await db_session.refresh(document)
    assert document.parse_status == DocumentParseStatus.FAILED

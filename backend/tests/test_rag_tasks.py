import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentParseStatus, DocumentRagStatus
from app.models.user import User
from app.workers.rag_tasks import _backfill_documents, _index_document
from tests.conftest import TestSessionLocal


async def create_document(db: AsyncSession, *, extracted_text: str) -> Document:
    user = User(email=f"{uuid.uuid4().hex}@example.com", full_name="RAG task test")
    db.add(user)
    await db.flush()
    document = Document(
        uploaded_by=user.id,
        filename="fixture.pdf",
        storage_path=f"fixtures/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_type="pdf",
        parse_status=DocumentParseStatus.DONE,
        extracted_text=extracted_text,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def test_index_document_marks_empty_content_failed(db_session: AsyncSession) -> None:
    document = await create_document(db_session, extracted_text="   ")

    with (
        patch("app.workers.rag_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.rag_tasks.get_settings") as settings,
        patch("app.workers.rag_tasks.run_task", new_callable=AsyncMock) as run_task,
    ):
        settings.return_value.rag_enabled = True
        await _index_document(document.id)

    await db_session.refresh(document)
    assert document.rag_status is DocumentRagStatus.FAILED
    run_task.assert_not_awaited()


async def test_backfill_skips_empty_extracted_text(db_session: AsyncSession) -> None:
    empty = await create_document(db_session, extracted_text="")
    indexable = await create_document(db_session, extracted_text="Index this paragraph.")

    with (
        patch("app.workers.rag_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.rag_tasks.get_settings") as settings,
        patch("app.workers.rag_tasks.index_document_task.delay") as delay,
    ):
        settings.return_value.rag_enabled = True
        dispatched = await _backfill_documents(batch_size=10)

    assert dispatched == 1
    delay.assert_called_once_with(str(indexable.id))
    assert delay.call_args.args[0] != str(empty.id)

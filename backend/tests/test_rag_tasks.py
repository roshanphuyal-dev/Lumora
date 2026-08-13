import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import ProviderName, TextEmbeddingResponse
from ai.orchestrator.task_types import TaskType
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentParseStatus, DocumentRagStatus
from app.models.user import User
from app.services import rag_index_service
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


async def test_index_document_marks_indexed_only_after_every_batch(
    db_session: AsyncSession,
) -> None:
    document = await create_document(db_session, extracted_text="Indexable content.")
    chunks = [AsyncMock(text=f"chunk-{index}") for index in range(21)]
    embedding_response = TextEmbeddingResponse(
        task_type=TaskType.TEXT_EMBEDDING,
        provider=ProviderName.GEMINI,
        embeddings=[[0.1] * 768 for _ in range(20)],
        model="gemini-embedding-001",
        dimensions=768,
    )

    with (
        patch("app.workers.rag_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.rag_tasks.get_settings") as settings,
        patch(
            "app.workers.rag_tasks.rag_index_service.build_chunks",
            new_callable=AsyncMock,
            return_value=chunks,
        ),
        patch(
            "app.workers.rag_tasks.rag_index_service.persist_embeddings",
            new_callable=AsyncMock,
        ) as persist_embeddings,
        patch(
            "app.workers.rag_tasks.run_task",
            new_callable=AsyncMock,
            side_effect=[embedding_response, OrchestrationError("second batch failed")],
        ),
    ):
        settings.return_value.rag_enabled = True
        with pytest.raises(OrchestrationError):
            await _index_document(document.id)

    await db_session.refresh(document)
    assert document.rag_status is DocumentRagStatus.FAILED
    persist_embeddings.assert_awaited_once()


async def test_index_document_skips_an_already_claimed_document(
    db_session: AsyncSession,
) -> None:
    document = await create_document(db_session, extracted_text="Indexable content.")
    document.rag_status = DocumentRagStatus.INDEXING
    await db_session.commit()

    with (
        patch("app.workers.rag_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.rag_tasks.get_settings") as settings,
        patch(
            "app.workers.rag_tasks.rag_index_service.build_chunks",
            new_callable=AsyncMock,
        ) as build_chunks,
        patch("app.workers.rag_tasks.run_task", new_callable=AsyncMock) as run_task,
    ):
        settings.return_value.rag_enabled = True
        await _index_document(document.id)

    build_chunks.assert_not_awaited()
    run_task.assert_not_awaited()


async def test_claim_document_allows_only_one_concurrent_claim(
    db_session: AsyncSession,
) -> None:
    document = await create_document(db_session, extracted_text="Indexable content.")

    async def claim() -> bool:
        async with TestSessionLocal() as db:
            return await rag_index_service.claim_document(db, document.id)

    results = await asyncio.gather(claim(), claim())

    assert sorted(results) == [False, True]

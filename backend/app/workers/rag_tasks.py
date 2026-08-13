"""Celery tasks for idempotent local chunking and embedding."""

import asyncio
import logging
import uuid

from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import EmbeddingPurpose, TextEmbeddingRequest
from ai.orchestrator.task_types import TaskType
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import celery_session_maker
from app.models.document import Document, DocumentParseStatus, DocumentRagStatus
from app.services import rag_index_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
_EMBEDDING_BATCH_SIZE = 20


@celery_app.task(
    name="rag.index_document",
    autoretry_for=(OrchestrationError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    rate_limit="30/m",
)
def index_document_task(document_id: str) -> None:
    asyncio.run(_index_document(uuid.UUID(document_id)))


async def _index_document(document_id: uuid.UUID) -> None:
    if not get_settings().rag_enabled:
        return
    async with celery_session_maker() as db:
        if not await rag_index_service.claim_document(db, document_id):
            return
        try:
            chunks = await rag_index_service.build_chunks(db, document_id)
            if not chunks:
                await rag_index_service.mark_failed(db, document_id)
                return
            for start in range(0, len(chunks), _EMBEDDING_BATCH_SIZE):
                batch = chunks[start : start + _EMBEDDING_BATCH_SIZE]
                response = await run_task(
                    TaskType.TEXT_EMBEDDING,
                    TextEmbeddingRequest(
                        texts=[chunk.text for chunk in batch], purpose=EmbeddingPurpose.DOCUMENT
                    ),
                )
                await rag_index_service.persist_embeddings(db, batch, response)
            await rag_index_service.mark_indexed(db, document_id)
        except Exception:
            await db.rollback()
            await rag_index_service.mark_failed(db, document_id)
            raise


@celery_app.task(name="rag.backfill_documents")
def backfill_documents_task(batch_size: int = 25) -> int:
    return asyncio.run(_backfill_documents(batch_size))


async def _backfill_documents(batch_size: int) -> int:
    if not get_settings().rag_enabled:
        return 0
    async with celery_session_maker() as db:
        ids = list(
            await db.scalars(
                select(Document.id)
                .where(
                    Document.parse_status == DocumentParseStatus.DONE,
                    Document.extracted_text.is_not(None),
                    func.length(func.trim(Document.extracted_text)) > 0,
                    Document.rag_status.in_([DocumentRagStatus.PENDING, DocumentRagStatus.FAILED]),
                )
                .order_by(Document.created_at)
                .limit(max(1, min(batch_size, 100)))
            )
        )
    for document_id in ids:
        index_document_task.delay(str(document_id))
    return len(ids)

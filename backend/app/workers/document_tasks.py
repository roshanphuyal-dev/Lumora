"""Celery tasks for the document parsing pipeline.

Celery workers run sync, but the rest of the app (DB session, services) is
async (see app/db/session.py) — rather than adding a second, sync DB stack
just for the worker, each task is a thin sync wrapper that drives the async
service calls with `asyncio.run`. This keeps `document_service` the single
source of truth for the DB writes, usable from both this task and any future
async API code.
"""

import asyncio
import logging
import uuid

from app.core.storage import get_file_storage
from app.db.session import celery_session_maker
from app.parsers import get_parser
from app.parsers.url_parser import parse_url
from app.services import document_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="documents.parse_document")
def parse_document_task(document_id: str) -> None:
    """Parse an uploaded Document's file and persist the extracted text.

    `document_id` is a str (not uuid.UUID) because Celery's JSON serializer
    can't carry UUIDs directly — callers should pass `str(document.id)`.
    """
    asyncio.run(_parse_document(uuid.UUID(document_id)))


async def _parse_document(document_id: uuid.UUID) -> None:
    async with celery_session_maker() as db:
        document = await document_service.mark_processing(db, document_id)

        try:
            if document.source_url is not None:
                parsed = await parse_url(document.source_url)
            else:
                file_bytes = await get_file_storage().download(document.storage_path)
                parser = get_parser(document.mime_type, document.file_type)
                parsed = parser(file_bytes)
        except Exception:
            logger.exception("Failed to parse document %s", document_id)
            await document_service.mark_parse_failed(db, document_id)
            return

        await document_service.mark_parsed(db, document_id, parsed)
        from app.core.config import get_settings

        if get_settings().rag_enabled:
            from app.workers.rag_tasks import index_document_task

            index_document_task.delay(str(document_id))

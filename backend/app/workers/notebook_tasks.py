"""Celery task for NotebookLM source indexing.

Mirrors `app/workers/document_tasks.py`'s sync-wrapper-over-async-service
pattern: Celery workers run sync, the rest of the app is async, so this task
is a thin sync wrapper that drives async service/orchestrator calls with
`asyncio.run`.

Indexing a source is two NotebookLM calls, not one:
  1. `NotebookLMClient.ensure_remote_notebook` resolves (creating on first use)
     the `Notebook`'s remote NotebookLM notebook id. This is a notebook-level
     concern, so it's called directly here rather than through
     `ai.orchestrator.run_task` — the orchestrator's `DOCUMENT_INDEX` task type
     only covers indexing one already-resolved notebook (see
     `ai/orchestrator/schemas.py:DocumentIndexRequest`). If this created a new
     remote notebook, the id is persisted back onto `Notebook` immediately so
     later sources for the same notebook reuse it instead of creating a new
     remote notebook each time.
  2. `ai.orchestrator.orchestrator.run_task(TaskType.DOCUMENT_INDEX, ...)` is
     the only entrypoint used for the actual upload/index call per
     `.claude/rules/ai.md` — this module never imports the NotebookLM CLI
     wrapper's indexing call directly, only `ensure_remote_notebook` above
     (which the orchestrator deliberately leaves to callers, see its
     docstring).

`nlm source add --file` needs a real local filesystem path (no bytes/stdin
mode), so the document's bytes are downloaded via `FileStorage.download` and
written to a temp file before indexing, then the temp file is removed in a
`finally` block regardless of outcome. A link-backed document (`source_url`
set, no `storage_path`) has no bytes to download — its already-extracted text
(`document.extracted_text`, populated by `document_tasks.parse_document_task`
before this task is ever dispatched — see `notebook_service.attach_source`'s
`parse_status == done` requirement) is written to the temp file instead.
"""

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

from ai.notebooklm.client import NotebookLMClient, NotebookLMError
from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import DocumentIndexRequest
from ai.orchestrator.task_types import TaskType

from app.core.storage import get_file_storage
from app.db.session import celery_session_maker
from app.services import document_service, notebook_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="notebooks.index_source")
def index_notebook_source_task(notebook_source_id: str) -> None:
    """Index a NotebookSource's document as a NotebookLM source.

    `notebook_source_id` is a str (not uuid.UUID) because Celery's JSON
    serializer can't carry UUIDs directly — callers should pass `str(source.id)`.
    """
    asyncio.run(_index_notebook_source(uuid.UUID(notebook_source_id)))


async def _index_notebook_source(notebook_source_id: uuid.UUID) -> None:
    async with celery_session_maker() as db:
        source = await notebook_service.get_source(db, notebook_source_id)
        document = await document_service.get_document(db, source.document_id)
        notebook = await notebook_service.get_notebook(db, source.notebook_id)

        tmp_path: Path | None = None
        try:
            remote_notebook_id = await NotebookLMClient().ensure_remote_notebook(
                notebooklm_notebook_id=notebook.notebooklm_notebook_id, name=notebook.name
            )
            if remote_notebook_id != notebook.notebooklm_notebook_id:
                notebook.notebooklm_notebook_id = remote_notebook_id
                await db.commit()

            if document.source_url is not None:
                content = (document.extracted_text or "").encode("utf-8")
                suffix = ".txt"
            else:
                content = await get_file_storage().download(document.storage_path)
                suffix = Path(document.filename).suffix
            tmp_path = await asyncio.to_thread(_write_temp_file, content, suffix)

            response = await run_task(
                TaskType.DOCUMENT_INDEX,
                DocumentIndexRequest(
                    document_id=str(document.id),
                    notebooklm_notebook_id=remote_notebook_id,
                    file_path=str(tmp_path),
                ),
            )
        except (NotebookLMError, OrchestrationError, FileNotFoundError):
            logger.exception("Failed to index notebook source %s", notebook_source_id)
            await notebook_service.mark_source_index_failed(db, notebook_source_id)
            return
        finally:
            if tmp_path is not None:
                await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

        await notebook_service.mark_source_indexed(
            db,
            notebook_source_id,
            getattr(response, "metadata", {}).get("notebooklm_source_id"),
        )


def _write_temp_file(content: bytes, suffix: str) -> Path:
    """Write `content` to a new temp file and return its path.

    Runs off the event loop via `asyncio.to_thread` (synchronous file I/O).
    `delete=False` because the file must outlive this function — the caller
    unlinks it in a `finally` block once indexing has finished/failed.
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        return Path(tmp.name)

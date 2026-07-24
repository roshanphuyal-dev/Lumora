"""File storage abstraction for `Document.storage_path`.

`FileStorage` is the swap point: `get_file_storage()` decides which
implementation backs it (`SupabaseFileStorage` vs the `LocalFileStorage`
dev/test stub). Nothing outside this module should know or care which one is
in use.

`upload` was added alongside the Document upload endpoint
(`app/api/v1/documents.py`) to persist the uploaded bytes somewhere
`download` can read them back from during parsing — see that endpoint's
docstring for why a real signed-upload-URL flow isn't implemented yet.
"""

import asyncio
from pathlib import Path
from typing import Protocol

from storage3._async.file_api import AsyncBucketProxy
from storage3.exceptions import StorageApiError
from supabase import create_async_client

from app.core.config import get_settings


class FileStorage(Protocol):
    """Fetches/persists raw file bytes for a Document given its `storage_path`."""

    async def download(self, storage_path: str) -> bytes:
        """Return the raw bytes stored at `storage_path`.

        Raises FileNotFoundError (or an implementation-specific equivalent)
        if nothing exists at that path.
        """
        ...

    async def upload(self, storage_path: str, content: bytes) -> None:
        """Persist `content` at `storage_path`, overwriting anything already there."""
        ...


class LocalFileStorage:
    """Dev/test stub: reads `storage_path` relative to a local root directory.

    NOT wired to Supabase Storage — this exists so the parsing pipeline is
    testable/runnable before that integration lands. Replace via
    `get_file_storage()` once it does.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path(get_settings().local_storage_root)

    async def download(self, storage_path: str) -> bytes:
        path = self._root / storage_path
        if not path.is_file():
            raise FileNotFoundError(f"No file at {path}")
        return await asyncio.to_thread(path.read_bytes)

    async def upload(self, storage_path: str, content: bytes) -> None:
        path = self._root / storage_path
        await asyncio.to_thread(self._write, path, content)

    @staticmethod
    def _write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


class SupabaseFileStorage:
    """Supabase Storage-backed `FileStorage`, using the private bucket
    `Settings.supabase_storage_bucket`.

    This is server-side, privileged access via the service-role key — NOT a
    client-facing signed-URL flow. A signed-URL flow for frontend-direct
    upload/download is a separate concern for once the frontend exists; it
    isn't built here (`docs/SECURITY.md` — never a public bucket).

    Uses `supabase-py`'s native async client (`create_async_client`, backed by
    `httpx.AsyncClient`) rather than wrapping the sync client in
    `asyncio.to_thread`, since the installed SDK (supabase-py 2.x) ships a
    real async storage API (`storage3._async`). A fresh client is created on
    every call rather than cached on the instance/module: Celery tasks
    (`app/workers/document_tasks.py`) drive this code via a new `asyncio.run`
    event loop per task, and caching an `httpx.AsyncClient` across separate
    event loops is unsafe (it binds to the loop that created it). Recreating
    the client is cheap (no network I/O — see `supabase.AsyncClient.create`);
    this trades a little connection-reuse for correctness across both the
    FastAPI request loop and the Celery per-task loop.
    """

    def __init__(
        self,
        url: str | None = None,
        service_role_key: str | None = None,
        bucket: str | None = None,
    ) -> None:
        settings = get_settings()
        self._url = url if url is not None else settings.supabase_url
        self._key = (
            service_role_key if service_role_key is not None else settings.supabase_service_role_key
        )
        self._bucket = bucket if bucket is not None else settings.supabase_storage_bucket
        if not self._url or not self._key:
            raise ValueError(
                "SupabaseFileStorage requires supabase_url and supabase_service_role_key "
                "to be set (app/core/config.py)"
            )

    async def _bucket_api(self) -> AsyncBucketProxy:
        client = await create_async_client(self._url, self._key)
        return client.storage.from_(self._bucket)

    async def download(self, storage_path: str) -> bytes:
        bucket = await self._bucket_api()
        try:
            return await bucket.download(storage_path)
        except StorageApiError as exc:
            if _is_not_found(exc):
                raise FileNotFoundError(f"No file at {storage_path}") from exc
            raise

    async def upload(self, storage_path: str, content: bytes) -> None:
        bucket = await self._bucket_api()
        # upsert="true" to match the protocol's "overwrite anything already
        # there" contract — Supabase's default POST /object rejects an
        # existing path with a 409 Duplicate.
        await bucket.upload(storage_path, content, {"upsert": "true"})


def _is_not_found(exc: StorageApiError) -> bool:
    """Best-effort translation of a Supabase Storage "object not found" error.

    NOT verified against a live Supabase project (no credentials available in
    this environment) — inferred from the Supabase Storage API, which returns
    a JSON body of the form `{"statusCode": "404", "error": "not_found", ...}`
    for a missing object. Checked defensively across `.status`/`.code` since
    `StorageApiError.status` may come through as either an int or a str.
    """
    status = str(exc.status).strip()
    code = (exc.code or "").lower()
    return status == "404" or code in {"not_found", "notfound"}


def get_file_storage() -> FileStorage:
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseFileStorage()
    return LocalFileStorage()

from types import SimpleNamespace

import pytest
from storage3.exceptions import StorageApiError

from app.core.storage import (
    LocalFileStorage,
    SupabaseFileStorage,
    _is_not_found,
    get_file_storage,
)


def _unconfigured_settings() -> SimpleNamespace:
    """Stand-in for `Settings` with no Supabase credentials set.

    Storage-selection/credential-requirement behavior must not depend on whatever the
    developer's real `backend/.env` happens to have in it (`app.core.storage.get_settings`
    is monkeypatched below rather than relying on the real one) -- otherwise these tests
    pass or fail based on local machine state instead of the code under test.
    """
    return SimpleNamespace(
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_storage_bucket="documents",
        local_storage_root="./storage",
    )


async def test_local_file_storage_reads_bytes(tmp_path) -> None:
    file_path = tmp_path / "notes.pdf"
    file_path.write_bytes(b"raw-bytes")
    storage = LocalFileStorage(root=tmp_path)

    result = await storage.download("notes.pdf")

    assert result == b"raw-bytes"


async def test_local_file_storage_raises_when_missing(tmp_path) -> None:
    storage = LocalFileStorage(root=tmp_path)

    with pytest.raises(FileNotFoundError):
        await storage.download("missing.pdf")


def test_get_file_storage_defaults_to_local_without_supabase_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.core.storage.get_settings", _unconfigured_settings)
    assert isinstance(get_file_storage(), LocalFileStorage)


def test_supabase_file_storage_requires_credentials(monkeypatch) -> None:
    monkeypatch.setattr("app.core.storage.get_settings", _unconfigured_settings)
    with pytest.raises(ValueError):
        SupabaseFileStorage(url=None, service_role_key=None, bucket="documents")


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        ("404", "not_found", True),
        (404, "not_found", True),
        ("400", "not_found", True),  # Supabase Storage wraps 404s in a 400 HTTP status
        ("400", "Duplicate", False),
        ("409", "Duplicate", False),
    ],
)
def test_is_not_found(status: str | int, code: str, expected: bool) -> None:
    exc = StorageApiError("message", code, status)
    assert _is_not_found(exc) is expected


class _FakeBucket:
    def __init__(self) -> None:
        self.uploaded: tuple[str, bytes, dict] | None = None

    async def download(self, path: str) -> bytes:
        raise StorageApiError("Object not found", "not_found", 400)

    async def upload(self, path: str, content: bytes, file_options: dict) -> None:
        self.uploaded = (path, content, file_options)


class _FakeStorage:
    def __init__(self, bucket: _FakeBucket) -> None:
        self._bucket = bucket

    def from_(self, bucket_name: str) -> _FakeBucket:
        return self._bucket


class _FakeClient:
    def __init__(self, bucket: _FakeBucket) -> None:
        self.storage = _FakeStorage(bucket)


async def test_supabase_file_storage_download_translates_not_found(monkeypatch) -> None:
    fake_bucket = _FakeBucket()

    async def fake_create_async_client(url: str, key: str) -> _FakeClient:
        return _FakeClient(fake_bucket)

    monkeypatch.setattr("app.core.storage.create_async_client", fake_create_async_client)
    storage = SupabaseFileStorage(url="https://x.supabase.co", service_role_key="key")

    with pytest.raises(FileNotFoundError):
        await storage.download("missing.pdf")


async def test_supabase_file_storage_upload_upserts(monkeypatch) -> None:
    fake_bucket = _FakeBucket()

    async def fake_create_async_client(url: str, key: str) -> _FakeClient:
        return _FakeClient(fake_bucket)

    monkeypatch.setattr("app.core.storage.create_async_client", fake_create_async_client)
    storage = SupabaseFileStorage(url="https://x.supabase.co", service_role_key="key")

    await storage.upload("a/b.pdf", b"raw-bytes")

    assert fake_bucket.uploaded == ("a/b.pdf", b"raw-bytes", {"upsert": "true"})

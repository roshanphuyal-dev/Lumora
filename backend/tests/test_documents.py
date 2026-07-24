import io
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.models.document import DocumentParseStatus


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-1", "full_name": "Test User"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correct-horse-1"}
    )
    return login.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fake_storage() -> AsyncMock:
    """`app.services.document_service.get_file_storage` seam.

    Upload tests only need `create_document` to persist a `Document` row and
    dispatch `parse_document_task` — they don't exercise real file I/O
    (that's `test_storage.py`'s job), so this avoids writing test artifacts
    into `backend/storage/` on every run.
    """
    storage = AsyncMock()
    storage.upload.return_value = None
    return storage


async def _upload_document(
    client: AsyncClient, token: str, *, filename: str = "notes.pdf", content: bytes = b"%PDF-fake%"
):
    with (
        patch("app.services.document_service.get_file_storage", return_value=_fake_storage()),
        patch("app.api.v1.documents.parse_document_task.delay") as mock_delay,
    ):
        resp = await client.post(
            "/api/v1/documents",
            files={"file": (filename, io.BytesIO(content), "application/pdf")},
            headers=_auth(token),
        )
    return resp, mock_delay


async def test_upload_creates_pending_document_and_dispatches_parse_task(
    client: AsyncClient, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)

    resp, mock_delay = await _upload_document(client, token)

    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "notes.pdf"
    assert body["parse_status"] == DocumentParseStatus.PENDING.value
    assert body["extracted_text"] is None
    mock_delay.assert_called_once_with(body["id"])


async def test_list_documents_is_paginated(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)
    for i in range(3):
        await _upload_document(client, token, filename=f"doc-{i}.pdf")

    resp = await client.get("/api/v1/documents?limit=2&offset=0", headers=_auth(token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


async def test_documents_are_isolated_per_user(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "doc-owner@example.com")
    token_b = await _register_and_login(client, "doc-intruder@example.com")

    await _upload_document(client, token_a, filename="only-a.pdf")

    resp = await client.get("/api/v1/documents", headers=_auth(token_b))

    assert resp.json()["total"] == 0


async def test_get_document_returns_parse_status_and_text(
    client: AsyncClient, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)
    upload_resp, _ = await _upload_document(client, token)
    document_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/documents/{document_id}", headers=_auth(token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == document_id
    assert body["parse_status"] == DocumentParseStatus.PENDING.value
    assert "extracted_text" in body


async def test_cannot_get_another_users_document(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "get-owner@example.com")
    token_b = await _register_and_login(client, "get-intruder@example.com")

    upload_resp, _ = await _upload_document(client, token_a)
    document_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/documents/{document_id}", headers=_auth(token_b))

    assert resp.status_code == 404


async def test_delete_document_removes_row(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)
    upload_resp, _ = await _upload_document(client, token)
    document_id = upload_resp.json()["id"]

    resp = await client.delete(f"/api/v1/documents/{document_id}", headers=_auth(token))
    assert resp.status_code == 204

    follow_up = await client.get(f"/api/v1/documents/{document_id}", headers=_auth(token))
    assert follow_up.status_code == 404


async def test_cannot_delete_another_users_document(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "del-owner@example.com")
    token_b = await _register_and_login(client, "del-intruder@example.com")

    upload_resp, _ = await _upload_document(client, token_a)
    document_id = upload_resp.json()["id"]

    resp = await client.delete(f"/api/v1/documents/{document_id}", headers=_auth(token_b))
    assert resp.status_code == 404

    # Still visible/owned by A -- the delete attempt by B must not have removed it.
    still_there = await client.get(f"/api/v1/documents/{document_id}", headers=_auth(token_a))
    assert still_there.status_code == 200

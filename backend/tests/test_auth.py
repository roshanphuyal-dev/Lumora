from unittest.mock import patch

from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, password: str = "correct-horse-1") -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Ada Lovelace"},
    )
    assert resp.status_code == 201, resp.text


async def test_register_then_login(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)

    resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "correct-horse-1"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


async def test_register_duplicate_email_rejected(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "another-pass-1", "full_name": "Someone Else"},
    )
    assert resp.status_code == 400


async def test_login_wrong_password_rejected(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_unknown_email_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever-1"}
    )
    assert resp.status_code == 401


async def test_refresh_token_issues_new_pair(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)
    login = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "correct-horse-1"}
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_rejects_access_token(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)
    login = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "correct-horse-1"}
    )
    access_token = login.json()["access_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


async def test_get_me_requires_valid_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401

    resp = await client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_get_me_returns_profile(client: AsyncClient, unique_email: str) -> None:
    await _register(client, unique_email)
    login = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "correct-horse-1"}
    )
    access_token = login.json()["access_token"]

    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == unique_email


async def test_google_login_creates_user(client: AsyncClient) -> None:
    fake_claims = {"sub": "google-uid-123", "email": "googler@example.com", "name": "Googler"}
    with patch(
        "app.services.auth_service.google_id_token.verify_oauth2_token",
        return_value=fake_claims,
    ):
        resp = await client.post("/api/v1/auth/google", json={"id_token": "fake-google-token"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_google_login_invalid_token_rejected(client: AsyncClient) -> None:
    with patch(
        "app.services.auth_service.google_id_token.verify_oauth2_token",
        side_effect=ValueError("bad token"),
    ):
        resp = await client.post("/api/v1/auth/google", json={"id_token": "garbage"})
    assert resp.status_code == 401

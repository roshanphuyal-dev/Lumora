from httpx import AsyncClient


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


async def test_create_and_list_courses(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)

    resp = await client.post(
        "/api/v1/courses", json={"name": "Linear Algebra"}, headers=_auth(token)
    )
    assert resp.status_code == 201

    resp = await client.get("/api/v1/courses", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Linear Algebra"


async def test_courses_are_isolated_per_user(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "user-a@example.com")
    token_b = await _register_and_login(client, "user-b@example.com")

    await client.post("/api/v1/courses", json={"name": "Only A's course"}, headers=_auth(token_a))

    resp = await client.get("/api/v1/courses", headers=_auth(token_b))
    assert resp.json()["total"] == 0


async def test_cannot_delete_another_users_course(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "owner@example.com")
    token_b = await _register_and_login(client, "intruder@example.com")

    create = await client.post(
        "/api/v1/courses", json={"name": "Owner's course"}, headers=_auth(token_a)
    )
    course_id = create.json()["id"]

    resp = await client.delete(f"/api/v1/courses/{course_id}", headers=_auth(token_b))
    assert resp.status_code == 404


async def test_subject_requires_owned_course(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "subj-owner@example.com")
    token_b = await _register_and_login(client, "subj-intruder@example.com")

    create = await client.post("/api/v1/courses", json={"name": "Physics"}, headers=_auth(token_a))
    course_id = create.json()["id"]

    resp = await client.post(
        f"/api/v1/courses/{course_id}/subjects",
        json={"name": "Mechanics"},
        headers=_auth(token_b),
    )
    assert resp.status_code == 404


async def test_create_and_list_subjects(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)
    create = await client.post("/api/v1/courses", json={"name": "Chemistry"}, headers=_auth(token))
    course_id = create.json()["id"]

    resp = await client.post(
        f"/api/v1/courses/{course_id}/subjects",
        json={"name": "Organic Chemistry"},
        headers=_auth(token),
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/courses/{course_id}/subjects", headers=_auth(token))
    assert resp.json()["total"] == 1


async def test_pagination_params(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)
    for i in range(3):
        await client.post("/api/v1/courses", json={"name": f"Course {i}"}, headers=_auth(token))

    resp = await client.get("/api/v1/courses?limit=2&offset=0", headers=_auth(token))
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3

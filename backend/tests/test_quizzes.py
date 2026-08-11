"""Router/service tests for `app.services.quiz_service` / `app.api.v1.quizzes`.

Mirrors `tests/test_flashcards.py`'s CRUD + ownership-scoping pattern.
"""

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook
from app.models.quiz import Quiz
from app.models.user import User


async def _register(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-1", "full_name": "Test User"},
    )
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correct-horse-1"}
    )
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_quiz_routes_are_owner_scoped_and_support_crud(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_token = await _register(client, "quiz-owner@example.com")
    other_token = await _register(client, "quiz-other@example.com")
    owner = await db_session.scalar(select(User).where(User.email == "quiz-owner@example.com"))
    assert owner is not None
    notebook = Notebook(owner_id=owner.id, name="Chemistry")
    db_session.add(notebook)
    await db_session.commit()
    await db_session.refresh(notebook)
    url = f"/api/v1/notebooks/{notebook.id}/quizzes"

    with patch("app.services.quiz_service.generate_quiz_task.delay") as delay:
        created = await client.post(
            url,
            json={"topic": "Stoichiometry", "question_types": ["mcq"], "question_count": 5},
            headers=_auth(owner_token),
        )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["questions"] == []
    delay.assert_called_once()
    quiz_id = created.json()["id"]

    listed = await client.get(url, headers=_auth(owner_token))
    assert listed.json()["total"] == 1

    # Ownership scoping: user B cannot list/get/delete user A's quiz -- 404, not 403,
    # matching get_owned_notebook/get_owned_quiz's not-found-not-forbidden convention.
    # Listing under a notebook the caller doesn't own 404s too (list_quizzes enforces
    # notebook ownership via get_owned_notebook before ever touching Quiz rows).
    assert (await client.get(url, headers=_auth(other_token))).status_code == 404
    assert (await client.get(f"{url}/{quiz_id}", headers=_auth(other_token))).status_code == 404
    assert (await client.delete(f"{url}/{quiz_id}", headers=_auth(other_token))).status_code == 404

    assert (await client.get(f"{url}/{quiz_id}", headers=_auth(owner_token))).status_code == 200
    assert (await client.delete(f"{url}/{quiz_id}", headers=_auth(owner_token))).status_code == 204
    assert (await client.get(f"{url}/{quiz_id}", headers=_auth(owner_token))).status_code == 404


async def test_get_quiz_not_found_for_nonexistent_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_token = await _register(client, "quiz-missing@example.com")
    owner = await db_session.scalar(select(User).where(User.email == "quiz-missing@example.com"))
    assert owner is not None
    notebook = Notebook(owner_id=owner.id, name="History")
    db_session.add(notebook)
    await db_session.commit()
    await db_session.refresh(notebook)

    response = await client.get(
        f"/api/v1/notebooks/{notebook.id}/quizzes/00000000-0000-0000-0000-000000000000",
        headers=_auth(owner_token),
    )
    assert response.status_code == 404


async def test_create_quiz_requires_owned_notebook(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A quiz can't be created under a notebook the caller doesn't own -- the parent
    notebook's ownership chain (`get_owned_notebook`) must be enforced, not just the
    quiz's own scoping once it exists."""
    await _register(client, "quiz-parent-owner@example.com")
    intruder_token = await _register(client, "quiz-parent-intruder@example.com")
    owner = await db_session.scalar(
        select(User).where(User.email == "quiz-parent-owner@example.com")
    )
    assert owner is not None
    notebook = Notebook(owner_id=owner.id, name="Geology")
    db_session.add(notebook)
    await db_session.commit()
    await db_session.refresh(notebook)

    with patch("app.services.quiz_service.generate_quiz_task.delay") as delay:
        response = await client.post(
            f"/api/v1/notebooks/{notebook.id}/quizzes",
            json={"topic": "Rocks", "question_types": ["mcq"], "question_count": 3},
            headers=_auth(intruder_token),
        )
    assert response.status_code == 404
    delay.assert_not_called()

    result = await db_session.scalars(select(Quiz).where(Quiz.notebook_id == notebook.id))
    assert list(result) == []

import json
from unittest.mock import AsyncMock, patch

from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import AIResponse, ProviderName
from ai.orchestrator.task_types import TaskType
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flashcard import Flashcard, FlashcardSet, FlashcardSetStatus
from app.models.notebook import Notebook
from app.models.user import User
from app.workers.flashcard_tasks import _generate_flashcards
from tests.conftest import TestSessionLocal


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


async def _user_notebook(db: AsyncSession, email: str) -> tuple[User, Notebook]:
    user = User(email=email, full_name="Test User")
    db.add(user)
    await db.flush()  # populate user.id before it's read below, per SQLAlchemy's default=uuid.uuid4
    notebook = Notebook(owner_id=user.id, name="Biology")
    db.add(notebook)
    await db.commit()
    await db.refresh(user)
    await db.refresh(notebook)
    return user, notebook


async def test_flashcard_routes_are_owner_scoped_and_support_crud(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_token = await _register(client, "cards-owner@example.com")
    other_token = await _register(client, "cards-other@example.com")
    owner = await db_session.scalar(select(User).where(User.email == "cards-owner@example.com"))
    assert owner is not None
    notebook = Notebook(owner_id=owner.id, name="Physics")
    db_session.add(notebook)
    await db_session.commit()
    await db_session.refresh(notebook)
    url = f"/api/v1/notebooks/{notebook.id}/flashcard-sets"

    with patch("app.services.flashcard_service.generate_flashcards_task.delay") as delay:
        created = await client.post(
            url, json={"topic": "Momentum", "count": 4}, headers=_auth(owner_token)
        )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["flashcards"] == []
    delay.assert_called_once()
    set_id = created.json()["id"]

    listed = await client.get(url, headers=_auth(owner_token))
    assert listed.json()["total"] == 1
    assert (await client.get(url, headers=_auth(other_token))).status_code == 404
    assert (await client.get(f"{url}/{set_id}", headers=_auth(other_token))).status_code == 404
    assert (await client.delete(f"{url}/{set_id}", headers=_auth(owner_token))).status_code == 204
    assert (await client.get(f"{url}/{set_id}", headers=_auth(owner_token))).status_code == 404


async def test_generate_flashcards_persists_ordered_cards(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "cards-worker@example.com")
    card_set = FlashcardSet(notebook_id=notebook.id, user_id=user.id, title="Cells")
    db_session.add(card_set)
    await db_session.commit()
    await db_session.refresh(card_set)
    content = json.dumps(
        [
            {"front": "What is a cell?", "back": "The basic unit of life.", "citation": None},
            {
                "front": "What contains DNA?",
                "back": "The nucleus.",
                "citation": {"source_id": "source-1"},
            },
        ]
    )
    response = AIResponse(
        task_type=TaskType.FLASHCARD_GENERATION,
        provider=ProviderName.GEMINI,
        content=content,
    )
    with (
        patch("app.workers.flashcard_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.flashcard_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _generate_flashcards(card_set.id)
    await db_session.refresh(card_set)
    cards = list(
        await db_session.scalars(
            select(Flashcard)
            .where(Flashcard.flashcard_set_id == card_set.id)
            .order_by(Flashcard.position)
        )
    )
    assert card_set.status is FlashcardSetStatus.DONE
    assert [(card.position, card.front) for card in cards] == [
        (0, "What is a cell?"),
        (1, "What contains DNA?"),
    ]
    assert cards[1].citation == {"source_id": "source-1", "chunk_id": None, "excerpt": None}


async def test_generate_flashcards_persists_failure(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "cards-failure@example.com")
    card_set = FlashcardSet(notebook_id=notebook.id, user_id=user.id, title="Cells")
    db_session.add(card_set)
    await db_session.commit()
    await db_session.refresh(card_set)
    with (
        patch("app.workers.flashcard_tasks.celery_session_maker", TestSessionLocal),
        patch(
            "app.workers.flashcard_tasks.run_task",
            new=AsyncMock(side_effect=OrchestrationError("providers unavailable")),
        ),
    ):
        await _generate_flashcards(card_set.id)
    await db_session.refresh(card_set)
    assert card_set.status is FlashcardSetStatus.FAILED
    assert card_set.error_message == "providers unavailable"


async def test_generate_flashcards_skips_grounding_without_indexed_remote_source(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "cards-grounding@example.com")
    card_set = FlashcardSet(notebook_id=notebook.id, user_id=user.id, title="Cells")
    db_session.add(card_set)
    await db_session.commit()
    await db_session.refresh(card_set)
    response = AIResponse(
        task_type=TaskType.FLASHCARD_GENERATION,
        provider=ProviderName.GEMINI,
        content="[]",
    )
    run_task = AsyncMock(return_value=response)
    with (
        patch("app.workers.flashcard_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.flashcard_tasks.run_task", new=run_task),
    ):
        await _generate_flashcards(card_set.id)
    run_task.assert_awaited_once()
    assert run_task.await_args.args[0] is TaskType.FLASHCARD_GENERATION
    assert run_task.await_args.args[1].context == ""

from unittest.mock import AsyncMock, patch

from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import AIResponse, Citation, ProviderName
from ai.orchestrator.task_types import TaskType
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note, NoteMaterialType, NoteStatus
from app.models.notebook import Notebook, NotebookSourceIndexStatus
from app.models.user import User
from app.workers.note_tasks import _generate_note
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


async def test_notes_routes_are_owner_scoped_and_support_crud(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_token = await _register(client, "notes-owner@example.com")
    other_token = await _register(client, "notes-other@example.com")
    from sqlalchemy import select

    owner = await db_session.scalar(select(User).where(User.email == "notes-owner@example.com"))
    assert owner is not None
    notebook = Notebook(owner_id=owner.id, name="Physics")
    db_session.add(notebook)
    await db_session.commit()
    await db_session.refresh(notebook)
    url = f"/api/v1/notebooks/{notebook.id}/notes"

    with patch("app.services.note_service.generate_note_task.delay") as delay:
        created = await client.post(
            url,
            json={"material_type": "study_guide", "topic": "Momentum"},
            headers=_auth(owner_token),
        )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["title"] == "Momentum"
    delay.assert_called_once()
    note_id = created.json()["id"]

    listed = await client.get(url, headers=_auth(owner_token))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert (await client.get(url, headers=_auth(other_token))).status_code == 404
    assert (await client.get(f"{url}/{note_id}", headers=_auth(other_token))).status_code == 404
    assert (await client.delete(f"{url}/{note_id}", headers=_auth(owner_token))).status_code == 204
    assert (await client.get(f"{url}/{note_id}", headers=_auth(owner_token))).status_code == 404


async def test_generate_note_persists_success(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "note-worker@example.com")
    note = Note(
        notebook_id=notebook.id,
        user_id=user.id,
        material_type=NoteMaterialType.NOTE,
        title="Cells",
        citations=[],
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)
    response = AIResponse(
        task_type=TaskType.NOTES_GENERATION,
        provider=ProviderName.GEMINI,
        content="# Cells",
        citations=[Citation(source_id="source-1")],
    )
    with (
        patch("app.workers.note_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.note_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _generate_note(note.id)
    await db_session.refresh(note)
    assert note.status is NoteStatus.DONE
    assert note.content == "# Cells"
    assert note.citations == [{"source_id": "source-1", "chunk_id": None, "excerpt": None}]


async def test_generate_note_persists_failure(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "note-failure@example.com")
    note = Note(
        notebook_id=notebook.id,
        user_id=user.id,
        material_type=NoteMaterialType.NOTE,
        title="Cells",
        citations=[],
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)
    with (
        patch("app.workers.note_tasks.celery_session_maker", TestSessionLocal),
        patch(
            "app.workers.note_tasks.run_task",
            new=AsyncMock(side_effect=OrchestrationError("providers unavailable")),
        ),
    ):
        await _generate_note(note.id)
    await db_session.refresh(note)
    assert note.status is NoteStatus.FAILED
    assert note.error_message == "providers unavailable"


async def test_generate_note_persists_structured_content_json(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "note-structured@example.com")
    note = Note(
        notebook_id=notebook.id,
        user_id=user.id,
        material_type=NoteMaterialType.MNEMONICS,
        title="Planets",
        citations=[],
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)
    response = AIResponse(
        task_type=TaskType.STRUCTURED_NOTE_GENERATION,
        provider=ProviderName.GEMINI,
        content=(
            '[{"label": "Order", "value": "My Very Educated...", '
            '"detail": "...", "citation": null}]'
        ),
        citations=[Citation(source_id="source-1")],
    )
    with (
        patch("app.workers.note_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.note_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _generate_note(note.id)
    await db_session.refresh(note)
    assert note.status is NoteStatus.DONE
    assert note.content is None
    assert note.content_json == [
        {"label": "Order", "value": "My Very Educated...", "detail": "...", "citation": None}
    ]


async def test_generate_note_persists_failure_on_malformed_structured_json(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _user_notebook(db_session, "note-malformed@example.com")
    note = Note(
        notebook_id=notebook.id,
        user_id=user.id,
        material_type=NoteMaterialType.COMPARISON_CHART,
        title="Mitosis vs Meiosis",
        citations=[],
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)
    response = AIResponse(
        task_type=TaskType.STRUCTURED_NOTE_GENERATION,
        provider=ProviderName.GEMINI,
        content="not valid json",
        citations=[],
    )
    with (
        patch("app.workers.note_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.note_tasks.run_task", new=AsyncMock(return_value=response)),
    ):
        await _generate_note(note.id)
    await db_session.refresh(note)
    assert note.status is NoteStatus.FAILED
    assert note.content_json is None
    assert note.error_message is not None


async def test_generate_note_uses_grounding_only_for_indexed_remote_notebook(
    db_session: AsyncSession,
) -> None:
    from app.models.document import Document, DocumentParseStatus
    from app.models.notebook import NotebookSource

    user, notebook = await _user_notebook(db_session, "note-grounding@example.com")
    notebook.notebooklm_notebook_id = "remote-1"
    document = Document(
        uploaded_by=user.id,
        filename="cells.pdf",
        storage_path="documents/cells.pdf",
        mime_type="application/pdf",
        file_type="pdf",
        parse_status=DocumentParseStatus.DONE,
    )
    db_session.add(document)
    await db_session.flush()
    db_session.add(
        NotebookSource(
            notebook_id=notebook.id,
            document_id=document.id,
            indexing_status=NotebookSourceIndexStatus.INDEXED,
        )
    )
    note = Note(
        notebook_id=notebook.id,
        user_id=user.id,
        material_type=NoteMaterialType.NOTE,
        title="Cells",
        citations=[],
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)
    retrieval = AIResponse(
        task_type=TaskType.NOTEBOOK_QUERY,
        provider=ProviderName.NOTEBOOKLM,
        content="Grounded cells",
        citations=[Citation(source_id="source-1")],
    )
    generated = AIResponse(
        task_type=TaskType.NOTES_GENERATION,
        provider=ProviderName.GEMINI,
        content="# Cells",
        citations=retrieval.citations,
    )
    generation_task = AsyncMock(return_value=generated)
    grounding_task = AsyncMock(return_value=retrieval)
    with (
        patch("app.workers.note_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.note_tasks.run_task", new=generation_task),
        patch("app.services.generation_grounding_service.run_task", new=grounding_task),
    ):
        await _generate_note(note.id)
    grounding_task.assert_awaited_once()
    assert grounding_task.await_args.args[0] is TaskType.NOTEBOOK_QUERY
    assert generation_task.await_args.args[0] is TaskType.NOTES_GENERATION
    assert generation_task.await_args.args[1].context == "Grounded cells"

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import AIResponse, ProviderName
from ai.orchestrator.task_types import TaskType
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentParseStatus
from app.models.generated_material import GeneratedMaterial, MaterialArtifactType, MaterialStatus
from app.models.notebook import Notebook, NotebookSource, NotebookSourceIndexStatus
from app.models.user import User
from app.workers.studio_tasks import _generate_studio_artifact
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


async def _user_notebook(
    db: AsyncSession, email: str, *, indexed: bool = True
) -> tuple[User, Notebook]:
    user = User(email=email, full_name="Test User")
    db.add(user)
    await db.flush()
    notebook = Notebook(
        owner_id=user.id,
        name="Biology",
        notebooklm_notebook_id="remote-notebook" if indexed else None,
    )
    db.add(notebook)
    await db.flush()
    if indexed:
        document = Document(
            uploaded_by=user.id,
            filename="biology.pdf",
            storage_path="documents/biology.pdf",
            mime_type="application/pdf",
            file_type="pdf",
            parse_status=DocumentParseStatus.DONE,
        )
        db.add(document)
        await db.flush()
        db.add(
            NotebookSource(
                notebook_id=notebook.id,
                document_id=document.id,
                indexing_status=NotebookSourceIndexStatus.INDEXED,
            )
        )
    await db.commit()
    await db.refresh(user)
    await db.refresh(notebook)
    return user, notebook


async def _material(
    db: AsyncSession,
    user: User,
    notebook: Notebook,
    artifact_type: MaterialArtifactType,
) -> GeneratedMaterial:
    material = GeneratedMaterial(
        notebook_id=notebook.id,
        user_id=user.id,
        artifact_type=artifact_type,
        title="Test material",
        options={},
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


def _response(*, content: str = "", remote_status: str = "unknown") -> AIResponse:
    return AIResponse(
        task_type=TaskType.STUDIO_ARTIFACT_CREATE,
        provider=ProviderName.NOTEBOOKLM,
        content=content,
        metadata={"notebooklm_artifact_id": "artifact-x", "status": remote_status},
    )


async def test_studio_routes_are_owner_scoped_and_support_crud(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_token = await _register(client, "studio-owner@example.com")
    other_token = await _register(client, "studio-other@example.com")
    owner = await db_session.scalar(select(User).where(User.email == "studio-owner@example.com"))
    assert owner is not None
    _, notebook = await _user_notebook(db_session, "studio-helper@example.com")
    notebook.owner_id = owner.id
    await db_session.commit()
    url = f"/api/v1/notebooks/{notebook.id}/studio"

    with patch(
        "app.services.generated_material_service.generate_studio_artifact_task.delay"
    ) as delay:
        created = await client.post(
            url, json={"artifact_type": "report"}, headers=_auth(owner_token)
        )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["has_download"] is False
    assert "storage_path" not in created.json()
    delay.assert_called_once()
    material_id = created.json()["id"]

    assert (await client.get(url, headers=_auth(owner_token))).json()["total"] == 1
    assert (await client.get(url, headers=_auth(other_token))).status_code == 404
    assert (await client.get(f"{url}/{material_id}", headers=_auth(other_token))).status_code == 404
    assert (await client.get(f"{url}/{material_id}", headers=_auth(owner_token))).status_code == 200
    deleted = await client.delete(f"{url}/{material_id}", headers=_auth(owner_token))
    assert deleted.status_code == 204
    assert (await client.get(f"{url}/{material_id}", headers=_auth(owner_token))).status_code == 404


async def test_create_rejects_unindexed_notebook_and_undescribed_data_table(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await _register(client, "studio-validation@example.com")
    user = await db_session.scalar(
        select(User).where(User.email == "studio-validation@example.com")
    )
    assert user is not None
    empty = Notebook(owner_id=user.id, name="Empty")
    db_session.add(empty)
    await db_session.commit()
    await db_session.refresh(empty)
    response = await client.post(
        f"/api/v1/notebooks/{empty.id}/studio",
        json={"artifact_type": "report"},
        headers=_auth(token),
    )
    assert response.status_code == 409

    _, indexed = await _user_notebook(db_session, "studio-indexed-helper@example.com")
    indexed.owner_id = user.id
    await db_session.commit()
    response = await client.post(
        f"/api/v1/notebooks/{indexed.id}/studio",
        json={"artifact_type": "data_table"},
        headers=_auth(token),
    )
    assert response.status_code == 422


async def test_report_task_polls_and_persists_text(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "studio-report@example.com")
    material = await _material(db_session, user, notebook, MaterialArtifactType.REPORT)

    async def write_report(**kwargs: str) -> None:
        Path(kwargs["output_path"]).write_text("# Generated report")

    with (
        patch("app.workers.studio_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.studio_tasks.run_task", new=AsyncMock(return_value=_response())),
        patch("app.workers.studio_tasks.asyncio.sleep", new=AsyncMock()),
        patch(
            "app.workers.studio_tasks.NotebookLMClient.get_studio_artifact_status",
            new=AsyncMock(side_effect=["unknown", "completed"]),
        ),
        patch(
            "app.workers.studio_tasks.NotebookLMClient.download_studio_artifact",
            new=AsyncMock(side_effect=write_report),
        ),
    ):
        await _generate_studio_artifact(material.id)
    await db_session.refresh(material)
    assert material.status is MaterialStatus.DONE
    assert material.content == "# Generated report"


async def test_mindmap_task_skips_poll_and_download(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "studio-mindmap@example.com")
    material = await _material(db_session, user, notebook, MaterialArtifactType.MINDMAP)
    poll = AsyncMock()
    download = AsyncMock()
    with (
        patch("app.workers.studio_tasks.celery_session_maker", TestSessionLocal),
        patch(
            "app.workers.studio_tasks.run_task",
            new=AsyncMock(
                return_value=_response(content='{"nodes": []}', remote_status="completed")
            ),
        ),
        patch("app.workers.studio_tasks.NotebookLMClient.get_studio_artifact_status", new=poll),
        patch("app.workers.studio_tasks.NotebookLMClient.download_studio_artifact", new=download),
    ):
        await _generate_studio_artifact(material.id)
    await db_session.refresh(material)
    assert material.status is MaterialStatus.DONE
    assert material.content == '{"nodes": []}'
    poll.assert_not_awaited()
    download.assert_not_awaited()


async def test_binary_task_uploads_downloaded_bytes(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "studio-image@example.com")
    material = await _material(db_session, user, notebook, MaterialArtifactType.INFOGRAPHIC)
    storage = MagicMock()
    storage.upload = AsyncMock()

    async def write_image(**kwargs: str) -> None:
        Path(kwargs["output_path"]).write_bytes(b"png-bytes")

    with (
        patch("app.workers.studio_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.studio_tasks.run_task", new=AsyncMock(return_value=_response())),
        patch("app.workers.studio_tasks.asyncio.sleep", new=AsyncMock()),
        patch(
            "app.workers.studio_tasks.NotebookLMClient.get_studio_artifact_status",
            new=AsyncMock(return_value="completed"),
        ),
        patch(
            "app.workers.studio_tasks.NotebookLMClient.download_studio_artifact",
            new=AsyncMock(side_effect=write_image),
        ),
        patch("app.workers.studio_tasks.get_file_storage", return_value=storage),
    ):
        await _generate_studio_artifact(material.id)
    await db_session.refresh(material)
    assert material.status is MaterialStatus.DONE
    assert material.content is None
    assert material.storage_path == f"generated_materials/{material.id}.png"
    assert material.mime_type == "image/png"
    storage.upload.assert_awaited_once_with(material.storage_path, b"png-bytes")


async def test_task_persists_failure_and_times_out(db_session: AsyncSession) -> None:
    user, notebook = await _user_notebook(db_session, "studio-failure@example.com")
    failed = await _material(db_session, user, notebook, MaterialArtifactType.REPORT)
    with (
        patch("app.workers.studio_tasks.celery_session_maker", TestSessionLocal),
        patch(
            "app.workers.studio_tasks.run_task",
            new=AsyncMock(side_effect=OrchestrationError("provider unavailable")),
        ),
    ):
        await _generate_studio_artifact(failed.id)
    await db_session.refresh(failed)
    assert failed.status is MaterialStatus.FAILED
    assert failed.error_message == "provider unavailable"

    timed_out = await _material(db_session, user, notebook, MaterialArtifactType.REPORT)
    with (
        patch("app.workers.studio_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.studio_tasks.run_task", new=AsyncMock(return_value=_response())),
        patch("app.workers.studio_tasks._MAX_WAIT_SECONDS", {"report": 0}),
        patch(
            "app.workers.studio_tasks.NotebookLMClient.get_studio_artifact_status",
            new=AsyncMock(return_value="unknown"),
        ),
    ):
        await _generate_studio_artifact(timed_out.id)
    await db_session.refresh(timed_out)
    assert timed_out.status is MaterialStatus.FAILED
    assert "did not complete within the expected time" in (timed_out.error_message or "")

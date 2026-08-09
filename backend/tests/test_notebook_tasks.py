import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from ai.orchestrator.orchestrator import OrchestrationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentParseStatus
from app.models.notebook import Notebook, NotebookSource, NotebookSourceIndexStatus
from app.models.user import User
from app.workers.notebook_tasks import _index_notebook_source
from tests.conftest import TestSessionLocal


async def _create_notebook_source(
    db_session: AsyncSession,
) -> tuple[Notebook, NotebookSource, Document]:
    user = User(email=f"{uuid.uuid4().hex[:12]}@example.com", full_name="Test User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    document = Document(
        uploaded_by=user.id,
        filename="notes.pdf",
        storage_path="documents/notes.pdf",
        mime_type="application/pdf",
        file_type="pdf",
        parse_status=DocumentParseStatus.DONE,
        extracted_text="parsed text",
    )
    notebook = Notebook(owner_id=user.id, name="Biology 101")
    db_session.add_all([document, notebook])
    await db_session.commit()
    await db_session.refresh(document)
    await db_session.refresh(notebook)

    source = NotebookSource(notebook_id=notebook.id, document_id=document.id)
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    return notebook, source, document


async def test_index_notebook_source_persists_remote_id_and_cleans_temp_file(
    db_session: AsyncSession,
) -> None:
    notebook, source, document = await _create_notebook_source(db_session)
    fake_storage = AsyncMock()
    fake_storage.download.return_value = b"%PDF-fake%"
    mock_notebooklm_client = AsyncMock()
    mock_notebooklm_client.ensure_remote_notebook.return_value = "nb-remote-1"
    temp_paths: list[Path] = []

    async def _assert_temp_file(*args: object, **_kwargs: object) -> None:
        request = args[1]
        file_path = Path(request.file_path)
        temp_paths.append(file_path)
        assert file_path.exists()
        assert file_path.read_bytes() == b"%PDF-fake%"

    with (
        patch("app.workers.notebook_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.notebook_tasks.get_file_storage", return_value=fake_storage),
        patch(
            "app.workers.notebook_tasks.NotebookLMClient",
            return_value=mock_notebooklm_client,
        ),
        patch(
            "app.workers.notebook_tasks.run_task", side_effect=_assert_temp_file
        ) as mock_run_task,
    ):
        await _index_notebook_source(source.id)

    await db_session.refresh(notebook)
    await db_session.refresh(source)

    mock_notebooklm_client.ensure_remote_notebook.assert_awaited_once_with(
        notebooklm_notebook_id=None, name=notebook.name
    )
    fake_storage.download.assert_awaited_once_with(document.storage_path)
    mock_run_task.assert_awaited_once()
    assert notebook.notebooklm_notebook_id == "nb-remote-1"
    assert source.indexing_status == NotebookSourceIndexStatus.INDEXED
    assert len(temp_paths) == 1
    assert not temp_paths[0].exists()


async def test_index_notebook_source_marks_failed_and_cleans_temp_file_on_error(
    db_session: AsyncSession,
) -> None:
    notebook, source, _document = await _create_notebook_source(db_session)
    fake_storage = AsyncMock()
    fake_storage.download.return_value = b"%PDF-fake%"
    mock_notebooklm_client = AsyncMock()
    mock_notebooklm_client.ensure_remote_notebook.return_value = "nb-remote-2"
    temp_paths: list[Path] = []

    async def _raise_index_error(*args: object, **_kwargs: object) -> None:
        request = args[1]
        file_path = Path(request.file_path)
        temp_paths.append(file_path)
        assert file_path.exists()
        raise OrchestrationError("CLI upload failed")

    with (
        patch("app.workers.notebook_tasks.celery_session_maker", TestSessionLocal),
        patch("app.workers.notebook_tasks.get_file_storage", return_value=fake_storage),
        patch(
            "app.workers.notebook_tasks.NotebookLMClient",
            return_value=mock_notebooklm_client,
        ),
        patch("app.workers.notebook_tasks.run_task", side_effect=_raise_index_error),
    ):
        await _index_notebook_source(source.id)

    await db_session.refresh(notebook)
    await db_session.refresh(source)

    assert notebook.notebooklm_notebook_id == "nb-remote-2"
    assert source.indexing_status == NotebookSourceIndexStatus.FAILED
    assert len(temp_paths) == 1
    assert not temp_paths[0].exists()

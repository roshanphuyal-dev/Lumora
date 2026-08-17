from unittest.mock import AsyncMock, patch

from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import AIResponse, Citation, ProviderName
from ai.orchestrator.task_types import TaskType
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.document import Document, DocumentParseStatus
from app.models.notebook import Notebook, NotebookSource, NotebookSourceIndexStatus
from app.models.user import User
from app.services.generation_grounding_service import get_generation_grounding
from app.services.rag_retrieval_service import LocalGrounding, LocalRetrievalError


async def _indexed_notebook(db: AsyncSession, email: str) -> tuple[User, Notebook]:
    user = User(email=email, full_name="Learner")
    db.add(user)
    await db.flush()
    notebook = Notebook(
        owner_id=user.id,
        name="Biology",
        notebooklm_notebook_id="remote-notebook",
    )
    db.add(notebook)
    document = Document(
        uploaded_by=user.id,
        filename="cells.pdf",
        storage_path="documents/cells.pdf",
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
    return user, notebook


async def test_local_fallback_supplies_authoritative_context_and_citations(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _indexed_notebook(db_session, "local-fallback@example.com")
    local = LocalGrounding(
        results=[],
        context="Local chunk context",
        citations=[Citation(source_id="source-local", chunk_id="chunk-local")],
    )
    settings = get_settings()
    previous = settings.rag_enabled
    settings.rag_enabled = True
    try:
        with (
            patch(
                "app.services.generation_grounding_service.run_task",
                new=AsyncMock(
                    return_value=AIResponse(
                        task_type=TaskType.NOTEBOOK_QUERY,
                        provider=ProviderName.NOTEBOOKLM,
                        content="Remote text without authoritative citations",
                        citations=[],
                    )
                ),
            ),
            patch(
                "app.services.generation_grounding_service.rag_retrieval_service.retrieve",
                new=AsyncMock(return_value=local),
            ) as retrieve,
        ):
            context, citations = await get_generation_grounding(
                db_session, user.id, notebook.id, "cells"
            )
    finally:
        settings.rag_enabled = previous

    retrieve.assert_awaited_once_with(db_session, user.id, notebook.id, "cells")
    assert context == "Local chunk context"
    assert citations == local.citations


async def test_adequate_notebooklm_grounding_skips_local_retrieval(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _indexed_notebook(db_session, "remote-adequate@example.com")
    remote = AIResponse(
        task_type=TaskType.NOTEBOOK_QUERY,
        provider=ProviderName.NOTEBOOKLM,
        content="Remote grounded context",
        citations=[Citation(source_id="remote-source")],
    )
    settings = get_settings()
    previous = settings.rag_enabled
    settings.rag_enabled = True
    try:
        with (
            patch(
                "app.services.generation_grounding_service.run_task",
                new=AsyncMock(return_value=remote),
            ),
            patch(
                "app.services.generation_grounding_service.rag_retrieval_service.retrieve",
                new=AsyncMock(),
            ) as retrieve,
        ):
            context, citations = await get_generation_grounding(
                db_session, user.id, notebook.id, "cells"
            )
    finally:
        settings.rag_enabled = previous

    retrieve.assert_not_awaited()
    assert context == remote.content
    assert citations == remote.citations


async def test_both_retrieval_failures_preserve_ungrounded_generation(
    db_session: AsyncSession,
) -> None:
    user, notebook = await _indexed_notebook(db_session, "grounding-fails@example.com")
    settings = get_settings()
    previous = settings.rag_enabled
    settings.rag_enabled = True
    try:
        with (
            patch(
                "app.services.generation_grounding_service.run_task",
                new=AsyncMock(side_effect=OrchestrationError("NotebookLM unavailable")),
            ),
            patch(
                "app.services.generation_grounding_service.rag_retrieval_service.retrieve",
                new=AsyncMock(side_effect=LocalRetrievalError("local unavailable")),
            ),
        ):
            context, citations = await get_generation_grounding(
                db_session, user.id, notebook.id, "cells"
            )
    finally:
        settings.rag_enabled = previous

    assert context == ""
    assert citations == []

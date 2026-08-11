import uuid
from unittest.mock import patch

from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import AIResponse, Citation, ProviderName
from ai.orchestrator.task_types import TaskType
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentParseStatus
from app.models.notebook import Notebook, NotebookSource, NotebookSourceIndexStatus
from app.models.user import User


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


async def _user_id(db_session: AsyncSession, email: str) -> str:
    user = await db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    return str(user.id)


async def _create_document(
    db_session: AsyncSession,
    uploaded_by: str,
    *,
    parse_status: DocumentParseStatus,
    filename: str = "notes.pdf",
) -> Document:
    document = Document(
        uploaded_by=uploaded_by,
        filename=filename,
        storage_path=filename,
        mime_type="application/pdf",
        file_type="pdf",
        parse_status=parse_status,
        extracted_text="parsed text" if parse_status == DocumentParseStatus.DONE else None,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


async def test_create_and_list_notebooks(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)

    resp = await client.post(
        "/api/v1/notebooks", json={"name": "Biology 101"}, headers=_auth(token)
    )
    assert resp.status_code == 201

    resp = await client.get("/api/v1/notebooks", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Biology 101"


async def test_notebooks_are_isolated_per_user(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "nb-owner@example.com")
    token_b = await _register_and_login(client, "nb-intruder@example.com")

    await client.post(
        "/api/v1/notebooks", json={"name": "Only A's notebook"}, headers=_auth(token_a)
    )

    resp = await client.get("/api/v1/notebooks", headers=_auth(token_b))
    assert resp.json()["total"] == 0


async def test_search_notebooks_by_name_or_description_is_owner_scoped(
    client: AsyncClient,
) -> None:
    token_a = await _register_and_login(client, "nb-search-owner@example.com")
    token_b = await _register_and_login(client, "nb-search-other@example.com")

    await client.post(
        "/api/v1/notebooks",
        json={"name": "Cell Biology", "description": "Mitochondria and respiration"},
        headers=_auth(token_a),
    )
    await client.post(
        "/api/v1/notebooks",
        json={"name": "Organic Chemistry", "description": "Reaction mechanisms"},
        headers=_auth(token_a),
    )
    await client.post(
        "/api/v1/notebooks",
        json={"name": "Private Biology", "description": "Mitochondria"},
        headers=_auth(token_b),
    )

    name_response = await client.get(
        "/api/v1/notebooks", params={"search": "BIOLOGY"}, headers=_auth(token_a)
    )
    description_response = await client.get(
        "/api/v1/notebooks", params={"search": "mitochondria"}, headers=_auth(token_a)
    )

    assert name_response.status_code == 200
    assert name_response.json()["total"] == 1
    assert name_response.json()["items"][0]["name"] == "Cell Biology"
    assert description_response.json()["total"] == 1
    assert description_response.json()["items"][0]["name"] == "Cell Biology"


async def test_search_notebooks_treats_wildcards_as_literal_text(
    client: AsyncClient, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)
    await client.post("/api/v1/notebooks", json={"name": "Physics 100%"}, headers=_auth(token))
    await client.post("/api/v1/notebooks", json={"name": "Physics basics"}, headers=_auth(token))

    response = await client.get("/api/v1/notebooks", params={"search": "%"}, headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["name"] == "Physics 100%"


async def test_cannot_get_or_delete_another_users_notebook(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "nbdel-owner@example.com")
    token_b = await _register_and_login(client, "nbdel-intruder@example.com")

    create = await client.post(
        "/api/v1/notebooks", json={"name": "Owner's notebook"}, headers=_auth(token_a)
    )
    notebook_id = create.json()["id"]

    get_resp = await client.get(f"/api/v1/notebooks/{notebook_id}", headers=_auth(token_b))
    assert get_resp.status_code == 404

    delete_resp = await client.delete(f"/api/v1/notebooks/{notebook_id}", headers=_auth(token_b))
    assert delete_resp.status_code == 404


async def test_attach_source_requires_parsed_document(
    client: AsyncClient, db_session: AsyncSession, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)
    user_id = await _user_id(db_session, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Chemistry"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    pending_document = await _create_document(
        db_session, user_id, parse_status=DocumentParseStatus.PENDING
    )

    with patch("app.api.v1.notebooks.index_notebook_source_task.delay") as mock_delay:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            json={"document_id": str(pending_document.id)},
            headers=_auth(token),
        )

    assert resp.status_code == 409
    mock_delay.assert_not_called()


async def test_attach_source_creates_source_and_dispatches_indexing(
    client: AsyncClient, db_session: AsyncSession, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)
    user_id = await _user_id(db_session, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Physics"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    done_document = await _create_document(
        db_session, user_id, parse_status=DocumentParseStatus.DONE
    )

    with patch("app.api.v1.notebooks.index_notebook_source_task.delay") as mock_delay:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            json={"document_id": str(done_document.id)},
            headers=_auth(token),
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["document_id"] == str(done_document.id)
    assert body["indexing_status"] == NotebookSourceIndexStatus.PENDING.value
    mock_delay.assert_called_once_with(body["id"])

    detail = await client.get(f"/api/v1/notebooks/{notebook_id}", headers=_auth(token))
    assert len(detail.json()["sources"]) == 1


async def test_attach_source_rejects_another_users_document(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token_a = await _register_and_login(client, "attach-owner@example.com")
    await _register_and_login(client, "attach-other@example.com")
    other_user_id = await _user_id(db_session, "attach-other@example.com")

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "A's notebook"}, headers=_auth(token_a)
    )
    notebook_id = notebook.json()["id"]

    other_users_document = await _create_document(
        db_session, other_user_id, parse_status=DocumentParseStatus.DONE
    )

    with patch("app.api.v1.notebooks.index_notebook_source_task.delay") as mock_delay:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            json={"document_id": str(other_users_document.id)},
            headers=_auth(token_a),
        )

    assert resp.status_code == 404
    mock_delay.assert_not_called()


async def test_detach_source_removes_it(
    client: AsyncClient, db_session: AsyncSession, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)
    user_id = await _user_id(db_session, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "History"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    done_document = await _create_document(
        db_session, user_id, parse_status=DocumentParseStatus.DONE
    )

    with patch("app.api.v1.notebooks.index_notebook_source_task.delay"):
        attach_resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            json={"document_id": str(done_document.id)},
            headers=_auth(token),
        )
    source_id = attach_resp.json()["id"]

    detach_resp = await client.delete(
        f"/api/v1/notebooks/{notebook_id}/sources/{source_id}", headers=_auth(token)
    )
    assert detach_resp.status_code == 204

    detail = await client.get(f"/api/v1/notebooks/{notebook_id}", headers=_auth(token))
    assert detail.json()["sources"] == []


async def test_cannot_detach_source_from_another_users_notebook(
    client: AsyncClient, db_session: AsyncSession, unique_email: str
) -> None:
    token_a = await _register_and_login(client, unique_email)
    token_b = await _register_and_login(client, "detach-intruder@example.com")
    user_id = await _user_id(db_session, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Geography"}, headers=_auth(token_a)
    )
    notebook_id = notebook.json()["id"]

    done_document = await _create_document(
        db_session, user_id, parse_status=DocumentParseStatus.DONE
    )

    with patch("app.api.v1.notebooks.index_notebook_source_task.delay"):
        attach_resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            json={"document_id": str(done_document.id)},
            headers=_auth(token_a),
        )
    source_id = attach_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/notebooks/{notebook_id}/sources/{source_id}", headers=_auth(token_b)
    )
    assert resp.status_code == 404


async def test_ask_returns_content_and_provider(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Chemistry"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    fake_response = AIResponse(
        task_type=TaskType.TEACHING_EXPLANATION,
        provider=ProviderName.GEMINI,
        content="A mole is 6.022e23 particles.",
        citations=[],
        metadata={},
    )
    with patch(
        "app.services.notebook_service.run_task", return_value=fake_response
    ) as mock_run_task:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/ask",
            json={"question": "What is a mole?"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "content": "A mole is 6.022e23 particles.",
        "provider": "gemini",
        "citations": [],
    }
    mock_run_task.assert_awaited_once()


async def test_ask_grounds_answer_in_notebooklm_when_a_source_is_indexed(
    client: AsyncClient, db_session: AsyncSession, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)
    user_id = await _user_id(db_session, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Biology"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    done_document = await _create_document(
        db_session, user_id, parse_status=DocumentParseStatus.DONE
    )
    with patch("app.api.v1.notebooks.index_notebook_source_task.delay"):
        attach_resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            json={"document_id": str(done_document.id)},
            headers=_auth(token),
        )
    source_id = attach_resp.json()["id"]

    # NotebookLM indexing normally lands these via the Celery worker
    # (`app/workers/notebook_tasks.py`) -- set directly since this test is only about the
    # ask flow reading an already-indexed state, not the indexing pipeline itself.
    notebook_row = await db_session.get(Notebook, uuid.UUID(notebook_id))
    assert notebook_row is not None
    notebook_row.notebooklm_notebook_id = "remote-nb-1"
    source_row = await db_session.get(NotebookSource, uuid.UUID(source_id))
    assert source_row is not None
    source_row.indexing_status = NotebookSourceIndexStatus.INDEXED
    await db_session.commit()

    retrieval_response = AIResponse(
        task_type=TaskType.NOTEBOOK_QUERY,
        provider=ProviderName.NOTEBOOKLM,
        content="Mitochondria is the powerhouse of the cell.",
        citations=[Citation(source_id="nlm-src-1")],
        metadata={},
    )
    teaching_response = AIResponse(
        task_type=TaskType.TEACHING_EXPLANATION,
        provider=ProviderName.GEMINI,
        content="The mitochondria produces the cell's energy (ATP).",
        citations=[Citation(source_id="nlm-src-1")],
        metadata={},
    )

    with patch(
        "app.services.notebook_service.run_task",
        side_effect=[retrieval_response, teaching_response],
    ) as mock_run_task:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/ask",
            json={"question": "What does the mitochondria do?"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "The mitochondria produces the cell's energy (ATP)."
    assert body["provider"] == "gemini"
    assert body["citations"] == [{"source_id": "nlm-src-1", "chunk_id": None, "excerpt": None}]

    assert mock_run_task.await_count == 2
    retrieve_call, teach_call = mock_run_task.await_args_list
    assert retrieve_call.args[0] == TaskType.NOTEBOOK_QUERY
    assert retrieve_call.args[1].notebooklm_notebook_id == "remote-nb-1"
    assert teach_call.args[0] == TaskType.TEACHING_EXPLANATION
    assert teach_call.args[1].context == "Mitochondria is the powerhouse of the cell."
    assert teach_call.args[1].citations == [Citation(source_id="nlm-src-1")]


async def test_ask_falls_back_to_ungrounded_answer_when_notebooklm_retrieval_fails(
    client: AsyncClient, db_session: AsyncSession, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)
    user_id = await _user_id(db_session, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "History"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    done_document = await _create_document(
        db_session, user_id, parse_status=DocumentParseStatus.DONE
    )
    with patch("app.api.v1.notebooks.index_notebook_source_task.delay"):
        attach_resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            json={"document_id": str(done_document.id)},
            headers=_auth(token),
        )
    source_id = attach_resp.json()["id"]

    notebook_row = await db_session.get(Notebook, uuid.UUID(notebook_id))
    assert notebook_row is not None
    notebook_row.notebooklm_notebook_id = "remote-nb-1"
    source_row = await db_session.get(NotebookSource, uuid.UUID(source_id))
    assert source_row is not None
    source_row.indexing_status = NotebookSourceIndexStatus.INDEXED
    await db_session.commit()

    teaching_response = AIResponse(
        task_type=TaskType.TEACHING_EXPLANATION,
        provider=ProviderName.GEMINI,
        content="A generic, ungrounded answer.",
        citations=[],
        metadata={},
    )

    with patch(
        "app.services.notebook_service.run_task",
        side_effect=[OrchestrationError("nlm CLI unavailable"), teaching_response],
    ) as mock_run_task:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/ask",
            json={"question": "What happened in 1066?"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    assert resp.json()["content"] == "A generic, ungrounded answer."
    assert mock_run_task.await_count == 2
    teach_call = mock_run_task.await_args_list[1]
    assert teach_call.args[1].context == ""


async def test_ask_404s_for_notebook_the_caller_does_not_own(
    client: AsyncClient, unique_email: str
) -> None:
    token_a = await _register_and_login(client, unique_email)
    token_b = await _register_and_login(client, "ask-intruder@example.com")

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Physics"}, headers=_auth(token_a)
    )
    notebook_id = notebook.json()["id"]

    with patch("app.services.notebook_service.run_task") as mock_run_task:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/ask",
            json={"question": "What is momentum?"},
            headers=_auth(token_b),
        )

    assert resp.status_code == 404
    mock_run_task.assert_not_awaited()


async def test_ask_returns_502_when_orchestrator_fails(
    client: AsyncClient, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)

    notebook = await client.post("/api/v1/notebooks", json={"name": "Math"}, headers=_auth(token))
    notebook_id = notebook.json()["id"]

    with patch(
        "app.services.notebook_service.run_task",
        side_effect=OrchestrationError("every provider failed"),
    ):
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/ask",
            json={"question": "What is a derivative?"},
            headers=_auth(token),
        )

    assert resp.status_code == 502
    assert "every provider failed" in resp.json()["detail"]


async def test_search_returns_content_and_provider(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Current Events"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    fake_response = AIResponse(
        task_type=TaskType.INTERNET_SEARCH,
        provider=ProviderName.GEMINI,
        content="The 2026 event happened last week.",
        citations=[Citation(source_id="https://example.com/article", excerpt="It happened.")],
        metadata={"search_provider": "tavily"},
    )
    with patch(
        "app.services.notebook_service.run_task", return_value=fake_response
    ) as mock_run_task:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/search",
            json={"query": "latest event 2026"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "content": "The 2026 event happened last week.",
        "provider": "gemini",
        "citations": [
            {
                "source_id": "https://example.com/article",
                "chunk_id": None,
                "excerpt": "It happened.",
            }
        ],
    }
    mock_run_task.assert_awaited_once()
    call = mock_run_task.await_args_list[0]
    assert call.args[0] == TaskType.INTERNET_SEARCH
    assert call.args[1].query == "latest event 2026"


async def test_search_404s_for_notebook_the_caller_does_not_own(
    client: AsyncClient, unique_email: str
) -> None:
    token_a = await _register_and_login(client, unique_email)
    token_b = await _register_and_login(client, "search-intruder@example.com")

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Physics"}, headers=_auth(token_a)
    )
    notebook_id = notebook.json()["id"]

    with patch("app.services.notebook_service.run_task") as mock_run_task:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/search",
            json={"query": "recent physics news"},
            headers=_auth(token_b),
        )

    assert resp.status_code == 404
    mock_run_task.assert_not_awaited()


async def test_search_returns_502_when_orchestrator_fails(
    client: AsyncClient, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)

    notebook = await client.post("/api/v1/notebooks", json={"name": "Math"}, headers=_auth(token))
    notebook_id = notebook.json()["id"]

    with patch(
        "app.services.notebook_service.run_task",
        side_effect=OrchestrationError("every provider failed"),
    ):
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/search",
            json={"query": "recent math news"},
            headers=_auth(token),
        )

    assert resp.status_code == 502
    assert "every provider failed" in resp.json()["detail"]


async def test_image_search_returns_found_result(client: AsyncClient, unique_email: str) -> None:
    token = await _register_and_login(client, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Biology"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    fake_response = AIResponse(
        task_type=TaskType.TOPIC_IMAGE_SEARCH,
        provider=ProviderName.WIKIMEDIA,
        content=(
            '{"image_url": "https://example.com/mito.jpg", '
            '"attribution": "Jane Doe", "license": "CC-BY-SA-4.0", '
            '"source_url": "https://commons.wikimedia.org/wiki/File:Mito.jpg"}'
        ),
        citations=[],
        metadata={"found": "true"},
    )
    with patch(
        "app.services.notebook_service.run_task", return_value=fake_response
    ) as mock_run_task:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/image-search",
            json={"query": "mitochondria"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "found": True,
        "image_url": "https://example.com/mito.jpg",
        "attribution": "Jane Doe",
        "license": "CC-BY-SA-4.0",
        "source_url": "https://commons.wikimedia.org/wiki/File:Mito.jpg",
    }
    mock_run_task.assert_awaited_once()
    call = mock_run_task.await_args_list[0]
    assert call.args[0] == TaskType.TOPIC_IMAGE_SEARCH
    assert call.args[1].query == "mitochondria"


async def test_image_search_returns_not_found_result_distinctly(
    client: AsyncClient, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Obscure Topic"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    fake_response = AIResponse(
        task_type=TaskType.TOPIC_IMAGE_SEARCH,
        provider=ProviderName.OPENVERSE,
        content="",
        citations=[],
        metadata={"found": "false"},
    )
    with patch("app.services.notebook_service.run_task", return_value=fake_response):
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/image-search",
            json={"query": "an extremely obscure niche topic"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "found": False,
        "image_url": None,
        "attribution": None,
        "license": None,
        "source_url": None,
    }


async def test_image_search_404s_for_notebook_the_caller_does_not_own(
    client: AsyncClient, unique_email: str
) -> None:
    token_a = await _register_and_login(client, unique_email)
    token_b = await _register_and_login(client, "image-search-intruder@example.com")

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Chemistry"}, headers=_auth(token_a)
    )
    notebook_id = notebook.json()["id"]

    with patch("app.services.notebook_service.run_task") as mock_run_task:
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/image-search",
            json={"query": "titration setup"},
            headers=_auth(token_b),
        )

    assert resp.status_code == 404
    mock_run_task.assert_not_awaited()


async def test_image_search_returns_502_when_orchestrator_fails(
    client: AsyncClient, unique_email: str
) -> None:
    token = await _register_and_login(client, unique_email)

    notebook = await client.post(
        "/api/v1/notebooks", json={"name": "Astronomy"}, headers=_auth(token)
    )
    notebook_id = notebook.json()["id"]

    with patch(
        "app.services.notebook_service.run_task",
        side_effect=OrchestrationError("every provider failed"),
    ):
        resp = await client.post(
            f"/api/v1/notebooks/{notebook_id}/image-search",
            json={"query": "black hole"},
            headers=_auth(token),
        )

    assert resp.status_code == 502
    assert "every provider failed" in resp.json()["detail"]

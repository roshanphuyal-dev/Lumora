import json
import uuid
from unittest.mock import AsyncMock

import pytest
from ai.orchestrator.orchestrator import OrchestrationError
from ai.orchestrator.schemas import (
    AIResponse,
    AIStreamChunk,
    ChatResponseRequest,
    Citation,
    ProviderName,
    TopicImageResult,
)
from ai.orchestrator.task_types import TaskType
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message, MessageKind, MessageRole
from app.models.document import Document, DocumentParseStatus
from app.models.notebook import Notebook, NotebookSource, NotebookSourceIndexStatus
from app.models.user import User
from app.services import chat_service


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-1", "full_name": "Test User"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-1"},
    )
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _user(db: AsyncSession, email: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


async def _notebook(
    db: AsyncSession,
    owner: User,
    *,
    name: str = "Physics",
    notebooklm_notebook_id: str | None = None,
) -> Notebook:
    notebook = Notebook(
        owner_id=owner.id,
        name=name,
        notebooklm_notebook_id=notebooklm_notebook_id,
    )
    db.add(notebook)
    await db.commit()
    await db.refresh(notebook)
    return notebook


async def _conversation(
    db: AsyncSession, owner: User, notebook: Notebook, *, title: str | None = None
) -> Conversation:
    conversation = Conversation(notebook_id=notebook.id, user_id=owner.id, title=title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def _add_source(
    db: AsyncSession,
    owner: User,
    notebook: Notebook,
    status: NotebookSourceIndexStatus,
) -> NotebookSource:
    document = Document(
        uploaded_by=owner.id,
        filename=f"{uuid.uuid4()}.pdf",
        storage_path=f"documents/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_type="pdf",
        parse_status=DocumentParseStatus.DONE,
        extracted_text="Source text",
    )
    db.add(document)
    await db.flush()
    source = NotebookSource(
        notebook_id=notebook.id,
        document_id=document.id,
        indexing_status=status,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def test_create_and_list_conversations_are_owner_scoped(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_token = await _register_and_login(client, "chat-owner@example.com")
    other_token = await _register_and_login(client, "chat-other@example.com")
    owner = await _user(db_session, "chat-owner@example.com")
    other = await _user(db_session, "chat-other@example.com")
    owner_notebook = await _notebook(db_session, owner)
    other_notebook = await _notebook(db_session, other, name="Private")

    created = await client.post(
        f"/api/v1/notebooks/{owner_notebook.id}/conversations",
        json={"title": "Kinematics"},
        headers=_auth(owner_token),
    )
    assert created.status_code == 201

    owner_list = await client.get(
        f"/api/v1/notebooks/{owner_notebook.id}/conversations",
        headers=_auth(owner_token),
    )
    assert [item["title"] for item in owner_list.json()] == ["Kinematics"]

    assert (
        await client.get(
            f"/api/v1/notebooks/{owner_notebook.id}/conversations",
            headers=_auth(other_token),
        )
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/notebooks/{other_notebook.id}/conversations",
            json={},
            headers=_auth(owner_token),
        )
    ).status_code == 404


async def test_conversation_and_messages_reject_wrong_owner_or_notebook(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register_and_login(client, "service-owner@example.com")
    await _register_and_login(client, "service-other@example.com")
    owner = await _user(db_session, "service-owner@example.com")
    other = await _user(db_session, "service-other@example.com")
    notebook = await _notebook(db_session, owner)
    wrong_notebook = await _notebook(db_session, owner, name="Wrong notebook")
    conversation = await _conversation(db_session, owner, notebook)

    for user_id, notebook_id in (
        (other.id, notebook.id),
        (owner.id, wrong_notebook.id),
    ):
        with pytest.raises(HTTPException) as conversation_error:
            await chat_service.get_owned_conversation(
                db_session, user_id, notebook_id, conversation.id
            )
        assert conversation_error.value.status_code == 404

        with pytest.raises(HTTPException) as messages_error:
            await chat_service.list_messages(db_session, user_id, notebook_id, conversation.id)
        assert messages_error.value.status_code == 404


async def test_prepare_stream_titles_conversation_and_persists_user_message(
    client: AsyncClient, db_session: AsyncSession, unique_email: str
) -> None:
    await _register_and_login(client, unique_email)
    owner = await _user(db_session, unique_email)
    notebook = await _notebook(db_session, owner)
    conversation = await _conversation(db_session, owner, notebook)

    user_message, request = await chat_service.prepare_stream(
        db_session, owner.id, notebook.id, conversation.id, "Explain momentum"
    )

    await db_session.refresh(conversation)
    persisted = await db_session.get(Message, user_message.id)
    assert conversation.title == "Explain momentum"
    assert persisted is not None
    assert persisted.role is MessageRole.USER
    assert persisted.content == "Explain momentum"
    assert request.question == "Explain momentum"


@pytest.mark.parametrize(
    ("remote_id", "source_status"),
    [
        (None, NotebookSourceIndexStatus.INDEXED),
        ("remote-notebook", NotebookSourceIndexStatus.PENDING),
    ],
)
async def test_prepare_stream_skips_grounding_without_both_requirements(
    client: AsyncClient,
    db_session: AsyncSession,
    unique_email: str,
    monkeypatch: pytest.MonkeyPatch,
    remote_id: str | None,
    source_status: NotebookSourceIndexStatus,
) -> None:
    await _register_and_login(client, unique_email)
    owner = await _user(db_session, unique_email)
    notebook = await _notebook(db_session, owner, notebooklm_notebook_id=remote_id)
    await _add_source(db_session, owner, notebook, source_status)
    conversation = await _conversation(db_session, owner, notebook)
    run_task = AsyncMock()
    monkeypatch.setattr(chat_service, "run_task", run_task)

    _, request = await chat_service.prepare_stream(
        db_session, owner.id, notebook.id, conversation.id, "Question"
    )

    run_task.assert_not_awaited()
    assert request.context == ""
    assert request.citations == []


async def test_prepare_stream_uses_grounding_and_swallows_retrieval_errors(
    client: AsyncClient,
    db_session: AsyncSession,
    unique_email: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _register_and_login(client, unique_email)
    owner = await _user(db_session, unique_email)
    notebook = await _notebook(db_session, owner, notebooklm_notebook_id="remote-notebook")
    await _add_source(db_session, owner, notebook, NotebookSourceIndexStatus.INDEXED)
    first = await _conversation(db_session, owner, notebook)
    second = await _conversation(db_session, owner, notebook)
    response = AIResponse(
        task_type=TaskType.NOTEBOOK_QUERY,
        provider=ProviderName.NOTEBOOKLM,
        content="Grounded context",
        citations=[],
    )
    run_task = AsyncMock(return_value=response)
    monkeypatch.setattr(chat_service, "run_task", run_task)

    _, request = await chat_service.prepare_stream(
        db_session, owner.id, notebook.id, first.id, "Ground this"
    )

    assert request.context == "Grounded context"
    assert run_task.await_args.args[0] is TaskType.NOTEBOOK_QUERY

    run_task.reset_mock()
    run_task.side_effect = OrchestrationError("retrieval unavailable")
    _, fallback_request = await chat_service.prepare_stream(
        db_session, owner.id, notebook.id, second.id, "Still answer"
    )
    run_task.assert_awaited_once()
    assert fallback_request.context == ""
    assert fallback_request.citations == []


async def test_stream_response_yields_sse_and_persists_assistant(
    client: AsyncClient,
    db_session: AsyncSession,
    unique_email: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _register_and_login(client, unique_email)
    owner = await _user(db_session, unique_email)
    notebook = await _notebook(db_session, owner)
    conversation = await _conversation(db_session, owner, notebook)
    user_message, request = await chat_service.prepare_stream(
        db_session, owner.id, notebook.id, conversation.id, "Question"
    )

    async def stream_task(task_type: TaskType, stream_request: ChatResponseRequest):
        assert task_type is TaskType.CHAT_RESPONSE
        assert stream_request is request
        yield AIStreamChunk(content="Hello ", provider=ProviderName.GEMINI)
        yield AIStreamChunk(content="world", provider=ProviderName.GEMINI)

    monkeypatch.setattr(chat_service, "stream_task", stream_task)
    events = [
        event
        async for event in chat_service.stream_response(
            db_session, conversation.id, user_message, request
        )
    ]

    assert events[0].startswith("event: start\n")
    assert sum(event.startswith("event: delta\n") for event in events) == 2
    assert events[-1].startswith("event: done\n")
    assistants = list(
        await db_session.scalars(
            select(Message).where(
                Message.conversation_id == conversation.id,
                Message.role == MessageRole.ASSISTANT,
            )
        )
    )
    assert len(assistants) == 1
    assert assistants[0].content == "Hello world"
    assert assistants[0].provider == ProviderName.GEMINI.value


async def test_stream_response_error_yields_error_without_persisting_assistant(
    client: AsyncClient,
    db_session: AsyncSession,
    unique_email: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _register_and_login(client, unique_email)
    owner = await _user(db_session, unique_email)
    notebook = await _notebook(db_session, owner)
    conversation = await _conversation(db_session, owner, notebook)
    user_message, request = await chat_service.prepare_stream(
        db_session, owner.id, notebook.id, conversation.id, "Question"
    )

    async def failing_stream_task(task_type: TaskType, stream_request: ChatResponseRequest):
        if False:
            yield
        raise OrchestrationError("provider unavailable")

    monkeypatch.setattr(chat_service, "stream_task", failing_stream_task)
    events = [
        event
        async for event in chat_service.stream_response(
            db_session, conversation.id, user_message, request
        )
    ]

    assert events[0].startswith("event: start\n")
    assert events[1].startswith("event: error\n")
    assert "provider unavailable" in json.loads(events[1].split("data: ", 1)[1])["detail"]
    assistant_count = await db_session.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.role == MessageRole.ASSISTANT,
        )
    )
    assert assistant_count == 0


async def test_conversation_routes_require_auth_and_hide_cross_user_messages(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_token = await _register_and_login(client, "route-owner@example.com")
    other_token = await _register_and_login(client, "route-other@example.com")
    owner = await _user(db_session, "route-owner@example.com")
    notebook = await _notebook(db_session, owner)

    create_url = f"/api/v1/notebooks/{notebook.id}/conversations"
    assert (await client.post(create_url, json={})).status_code in {401, 403}
    created = await client.post(create_url, json={}, headers=_auth(owner_token))
    assert created.status_code == 201

    messages_url = f"{create_url}/{created.json()['id']}/messages"
    assert (await client.get(messages_url)).status_code in {401, 403}
    assert (await client.get(messages_url, headers=_auth(other_token))).status_code == 404
    owner_response = await client.get(messages_url, headers=_auth(owner_token))
    assert owner_response.status_code == 200
    assert owner_response.json() == []


async def test_conversation_web_search_persists_pair_in_message_history(
    client: AsyncClient,
    db_session: AsyncSession,
    unique_email: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await _register_and_login(client, unique_email)
    owner = await _user(db_session, unique_email)
    notebook = await _notebook(db_session, owner)
    conversation = await _conversation(db_session, owner, notebook)
    search_web = AsyncMock(
        return_value=(
            "Paris hosted the 2024 Summer Olympics.",
            "gemini",
            [Citation(source_id="https://example.com/olympics", excerpt="Paris 2024")],
        )
    )
    monkeypatch.setattr(chat_service.notebook_service, "search_web", search_web)
    base_url = f"/api/v1/notebooks/{notebook.id}/conversations/{conversation.id}"

    response = await client.post(
        f"{base_url}/search",
        json={"query": "Where were the latest Summer Olympics?"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_message"]["kind"] == "web_search"
    assert payload["assistant_message"]["kind"] == "web_search"
    assert payload["assistant_message"]["citations"][0]["source_id"] == (
        "https://example.com/olympics"
    )

    history = await client.get(f"{base_url}/messages", headers=_auth(token))
    assert history.status_code == 200
    assert [(item["role"], item["kind"]) for item in history.json()] == [
        ("user", "web_search"),
        ("assistant", "web_search"),
    ]
    assert history.json()[1]["citations"] == payload["assistant_message"]["citations"]


async def test_conversation_paper_search_persists_pair_in_message_history(
    client: AsyncClient,
    db_session: AsyncSession,
    unique_email: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await _register_and_login(client, unique_email)
    owner = await _user(db_session, unique_email)
    notebook = await _notebook(db_session, owner)
    conversation = await _conversation(db_session, owner, notebook)
    search_papers = AsyncMock(
        return_value=(
            "Attention Is All You Need introduced the Transformer architecture.",
            "gemini",
            [Citation(source_id="https://arxiv.org/abs/1706.03762", excerpt="Transformer")],
        )
    )
    monkeypatch.setattr(chat_service.notebook_service, "search_papers", search_papers)
    base_url = f"/api/v1/notebooks/{notebook.id}/conversations/{conversation.id}"

    response = await client.post(
        f"{base_url}/paper-search",
        json={"query": "What paper introduced the Transformer?"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_message"]["kind"] == "paper_search"
    assert payload["assistant_message"]["kind"] == "paper_search"
    assert payload["assistant_message"]["citations"][0]["source_id"] == (
        "https://arxiv.org/abs/1706.03762"
    )

    history = await client.get(f"{base_url}/messages", headers=_auth(token))
    assert history.status_code == 200
    assert [(item["role"], item["kind"]) for item in history.json()] == [
        ("user", "paper_search"),
        ("assistant", "paper_search"),
    ]
    assert history.json()[1]["citations"] == payload["assistant_message"]["citations"]


async def test_conversation_paper_search_requires_auth_and_ownership(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_token = await _register_and_login(client, "paper-search-owner@example.com")
    other_token = await _register_and_login(client, "paper-search-other@example.com")
    owner = await _user(db_session, "paper-search-owner@example.com")
    notebook = await _notebook(db_session, owner)
    conversation = await _conversation(db_session, owner, notebook)
    search_papers = AsyncMock(return_value=("content", "gemini", []))
    monkeypatch.setattr(chat_service.notebook_service, "search_papers", search_papers)
    url = f"/api/v1/notebooks/{notebook.id}/conversations/{conversation.id}/paper-search"

    assert (await client.post(url, json={"query": "q"})).status_code in {401, 403}
    assert (
        await client.post(url, json={"query": "q"}, headers=_auth(other_token))
    ).status_code == 404
    owner_response = await client.post(url, json={"query": "q"}, headers=_auth(owner_token))
    assert owner_response.status_code == 200
    search_papers.assert_awaited_once()


async def test_attach_message_image_persists_result_in_message_history(
    client: AsyncClient,
    db_session: AsyncSession,
    unique_email: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await _register_and_login(client, unique_email)
    owner = await _user(db_session, unique_email)
    notebook = await _notebook(db_session, owner)
    conversation = await _conversation(db_session, owner, notebook)
    assistant = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        kind=MessageKind.NOTEBOOK,
        content="Photosynthesis turns light into chemical energy.",
        citations=[],
    )
    db_session.add(assistant)
    await db_session.commit()
    await db_session.refresh(assistant)
    image = TopicImageResult(
        image_url="https://images.example/photosynthesis.jpg",
        attribution="Example Photographer",
        license="CC BY 4.0",
        source_url="https://example.com/photosynthesis",
    )
    monkeypatch.setattr(
        chat_service.notebook_service,
        "search_topic_image",
        AsyncMock(return_value=image),
    )
    base_url = f"/api/v1/notebooks/{notebook.id}/conversations/{conversation.id}"

    response = await client.put(
        f"{base_url}/messages/{assistant.id}/image",
        json={"query": "photosynthesis"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert response.json()["image_result"] == image.model_dump()
    history = await client.get(f"{base_url}/messages", headers=_auth(token))
    assert history.status_code == 200
    assert history.json()[0]["id"] == str(assistant.id)
    assert history.json()[0]["image_result"] == image.model_dump()

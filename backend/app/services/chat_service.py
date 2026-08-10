import json
import uuid
from collections.abc import AsyncIterator

from ai.orchestrator.orchestrator import OrchestrationError, run_task, stream_task
from ai.orchestrator.schemas import ChatResponseRequest, Citation, NotebookQueryRequest
from ai.orchestrator.task_types import TaskType
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message, MessageRole
from app.models.notebook import NotebookSourceIndexStatus
from app.services.notebook_service import get_owned_notebook

_HISTORY_MESSAGE_LIMIT = 20
_HISTORY_CHARACTER_LIMIT = 12_000


async def create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    *,
    title: str | None = None,
) -> Conversation:
    await get_owned_notebook(db, user_id, notebook_id)
    conversation = Conversation(notebook_id=notebook_id, user_id=user_id, title=title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID
) -> list[Conversation]:
    await get_owned_notebook(db, user_id, notebook_id)
    result = await db.scalars(
        select(Conversation)
        .where(Conversation.notebook_id == notebook_id, Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
    )
    return list(result)


async def get_owned_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation:
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.notebook_id == notebook_id,
            Conversation.user_id == user_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


async def list_messages(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> list[Message]:
    await get_owned_conversation(db, user_id, notebook_id, conversation_id)
    result = await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result)


async def prepare_stream(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    conversation_id: uuid.UUID,
    content: str,
) -> tuple[Message, ChatResponseRequest]:
    conversation = await get_owned_conversation(db, user_id, notebook_id, conversation_id)
    notebook = await get_owned_notebook(db, user_id, notebook_id)
    history = await _recent_history(db, conversation_id)

    user_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=content,
        citations=[],
    )
    db.add(user_message)
    if conversation.title is None:
        conversation.title = content[:255]
    await db.commit()
    await db.refresh(user_message)

    context = ""
    citations: list[Citation] = []
    has_indexed_source = any(
        source.indexing_status == NotebookSourceIndexStatus.INDEXED for source in notebook.sources
    )
    if notebook.notebooklm_notebook_id and has_indexed_source:
        try:
            retrieval = await run_task(
                TaskType.NOTEBOOK_QUERY,
                NotebookQueryRequest(
                    notebooklm_notebook_id=notebook.notebooklm_notebook_id,
                    question=content,
                ),
            )
        except OrchestrationError:
            pass
        else:
            context = retrieval.content
            citations = retrieval.citations

    return user_message, ChatResponseRequest(
        question=content,
        context=context,
        history=history,
        citations=citations,
    )


async def stream_response(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_message: Message,
    request: ChatResponseRequest,
) -> AsyncIterator[str]:
    assistant_id = uuid.uuid4()
    yield _sse(
        "start", {"user_message": _message_payload(user_message), "assistant_id": str(assistant_id)}
    )

    content_parts: list[str] = []
    provider: str | None = None
    try:
        async for chunk in stream_task(TaskType.CHAT_RESPONSE, request):
            provider = chunk.provider.value
            content_parts.append(chunk.content)
            yield _sse("delta", {"content": chunk.content})
    except OrchestrationError as exc:
        yield _sse("error", {"detail": str(exc)})
        return

    assistant = Message(
        id=assistant_id,
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content="".join(content_parts),
        provider=provider,
        citations=[citation.model_dump() for citation in request.citations],
    )
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)
    yield _sse("done", {"message": _message_payload(assistant)})


async def _recent_history(db: AsyncSession, conversation_id: uuid.UUID) -> str:
    result = await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(_HISTORY_MESSAGE_LIMIT)
    )
    lines = [f"{message.role.value}: {message.content}" for message in reversed(list(result))]
    history = "\n".join(lines)
    return history[-_HISTORY_CHARACTER_LIMIT:]


def _message_payload(message: Message) -> dict[str, object]:
    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "role": message.role.value,
        "content": message.content,
        "provider": message.provider,
        "citations": message.citations,
        "created_at": message.created_at.isoformat(),
    }


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

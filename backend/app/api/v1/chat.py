import uuid

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.chat import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageImageCreate,
    MessageRead,
    WebSearchCreate,
    WebSearchMessagePair,
)
from app.services import chat_service

router = APIRouter(prefix="/notebooks/{notebook_id}/conversations", tags=["chat"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    notebook_id: uuid.UUID,
    payload: ConversationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationRead:
    conversation = await chat_service.create_conversation(
        db, current_user.id, notebook_id, title=payload.title
    )
    return ConversationRead.model_validate(conversation)


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    notebook_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> list[ConversationRead]:
    conversations = await chat_service.list_conversations(db, current_user.id, notebook_id)
    return [ConversationRead.model_validate(item) for item in conversations]


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    notebook_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> list[MessageRead]:
    messages = await chat_service.list_messages(db, current_user.id, notebook_id, conversation_id)
    return [MessageRead.model_validate(item) for item in messages]


@router.post("/{conversation_id}/messages/stream")
async def stream_message(
    notebook_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    user_message, request = await chat_service.prepare_stream(
        db, current_user.id, notebook_id, conversation_id, payload.content
    )
    return StreamingResponse(
        chat_service.stream_response(db, conversation_id, user_message, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{conversation_id}/search", response_model=WebSearchMessagePair)
async def search_web(
    notebook_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: WebSearchCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> WebSearchMessagePair:
    user_message, assistant_message = await chat_service.search_web(
        db, current_user.id, notebook_id, conversation_id, payload.query
    )
    return WebSearchMessagePair(
        user_message=MessageRead.model_validate(user_message),
        assistant_message=MessageRead.model_validate(assistant_message),
    )


@router.post("/{conversation_id}/paper-search", response_model=WebSearchMessagePair)
async def search_papers(
    notebook_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: WebSearchCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> WebSearchMessagePair:
    user_message, assistant_message = await chat_service.search_papers(
        db, current_user.id, notebook_id, conversation_id, payload.query
    )
    return WebSearchMessagePair(
        user_message=MessageRead.model_validate(user_message),
        assistant_message=MessageRead.model_validate(assistant_message),
    )


@router.put(
    "/{conversation_id}/messages/{message_id}/image",
    response_model=MessageRead,
)
async def attach_message_image(
    notebook_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: MessageImageCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageRead:
    message = await chat_service.attach_message_image(
        db,
        current_user.id,
        notebook_id,
        conversation_id,
        message_id,
        payload.query,
    )
    return MessageRead.model_validate(message)

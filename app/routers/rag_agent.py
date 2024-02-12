from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.schemas.message import CreateMessageRequest, RAGAgentMessageResponse
from app.services.messages.rag_agent.message_service import RAGAgentMessageService


router = APIRouter(prefix="/api/rag_agent", tags=["RAG agent"])


@router.post("/{chat_id}/messages")
async def create_message(
    chat_id: UUID, request: CreateMessageRequest, message_service: Annotated[RAGAgentMessageService, Depends()]
):
    return message_service.create_user_message(message_text=request.prompt)


@router.get("/{chat_id}/messages")
async def get_messages(
    chat_id: UUID,
    get_message_service: Annotated[RAGAgentMessageService, Depends()],
):
    return get_message_service.get_messages()

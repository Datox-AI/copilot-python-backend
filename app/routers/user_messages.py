from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.schemas.message import CreateMessageRequest, UpdateMessageRequest, UserMessageResponse
from app.services.messages import UserMessageService

router = APIRouter(prefix="/api/chats", tags=["User messages"])


@router.post("/{chat_id}/messages")
async def create_message(
    chat_id: UUID, request: CreateMessageRequest, message_service: Annotated[UserMessageService, Depends()]
):
    chat_exists = message_service.check_chat_exists(chat_id)
    if not chat_exists:
        raise HTTPException(status_code=404, detail="Chat not found")
    response_generator = message_service.create_message(request)
    return StreamingResponse(response_generator, media_type="text/event-stream")


@router.get("/{chat_id}/messages", response_model=list[UserMessageResponse])
async def get_messages(chat_id: UUID, message_service: UserMessageService = Depends(UserMessageService)):
    if not message_service.check_chat_exists(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return message_service.get_messages(chat_id)


@router.delete("/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    chat_id: UUID, message_id: UUID, message_service: UserMessageService = Depends(UserMessageService)
):
    if not message_service.check_chat_exists(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    if not message_service.delete_message(chat_id, message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{chat_id}/messages/{message_id}", response_model=UserMessageResponse)
async def update_message(
    chat_id: UUID,
    message_id: UUID,
    updated_data: UpdateMessageRequest,
    message_service: UserMessageService = Depends(UserMessageService),
):
    if not message_service.check_chat_exists(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    updated_message = message_service.update_message(chat_id, message_id, updated_data)
    if not updated_message:
        raise HTTPException(status_code=404, detail="Message not found")
    return updated_message


@router.delete("/{chat_id}/messages/batch", status_code=status.HTTP_204_NO_CONTENT)
async def delete_messages_batch(
    chat_id: UUID, message_ids: list[UUID], message_service: UserMessageService = Depends(UserMessageService)
):
    if not message_service.check_chat_exists(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    message_service.delete_messages_batch(chat_id, message_ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.schemas.message import MessageResponse
from app.services.messages.get_message import MessageGetService

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.get("/{chat_id}", response_model=list[MessageResponse])
async def get_messages(
    chat_id: UUID,
    get_message_service: Annotated[MessageGetService, Depends()],
):
    # return None
    return get_message_service.get_messages(chat_id=chat_id)

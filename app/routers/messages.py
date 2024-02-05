from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.schemas.message import AnalyticAgentMessageResponse
from app.services.messages.analytics_agent.get_message import MessageGetService

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.get("/{chat_id}", response_model=list[AnalyticAgentMessageResponse])
async def get_messages(
    chat_id: UUID,
    get_message_service: Annotated[MessageGetService, Depends()],
):
    # return None
    return get_message_service.get_messages(chat_id=chat_id)

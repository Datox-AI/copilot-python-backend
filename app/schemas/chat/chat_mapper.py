from datetime import datetime
from typing import Optional
from app.models.maindb import Chat
from app.schemas.chat import ChatResponse, ChatHistoryResponse

from app.schemas.message import MessageResponse


class ChatMapper:
    @staticmethod
    def map_to_chat_response(
        chat: Chat,
        messages_count: int,
        files_count: int,
        last_message: Optional[datetime] = None,
    ) -> ChatResponse:
        return ChatResponse(
            id=chat.id,
            name=chat.name,
            created=chat.created_at,
            pinned=chat.pinned,
            pinned_date=chat.pinned_date,
            type=chat.type,
            messages_count=messages_count,
            files_count=files_count,
            last_message=last_message,
            snowflake_data=chat.snowflake_data
        )

    @staticmethod
    def map_to_chat_history_response(chat: Chat):
        message_responses = [
            MessageResponse(
                id=message.id,
                chat_id=message.chat_id,
                text=message.text,
                role=message.role,
            )
            for message in chat.messages
        ]
        return ChatHistoryResponse(
            id=chat.id,
            name=chat.name,
            created=chat.created_at,
            type=chat.type,
            messages=message_responses,
        )

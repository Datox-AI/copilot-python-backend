from datetime import datetime
from typing import Optional
from app.models.maindb import Chat
from app.schemas.chat import ChatResponse

class ChatMapper:
    @staticmethod
    def map_to_chat_response(chat: Chat, messages_count: int, files_count: int, last_message: Optional[datetime] = None) -> ChatResponse:
        return ChatResponse(
            id=chat.id,
            name=chat.name,
            created=chat.created,
            pinned=chat.pinned,
            pinned_date=chat.pinned_date,
            type=chat.type,
            messages_count=messages_count,
            files_count=files_count,
            last_message=last_message
        )
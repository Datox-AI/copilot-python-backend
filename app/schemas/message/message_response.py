from app.schemas.base import BaseSchema
from app.enums.message_enums import MessageRole
from uuid import UUID


class MessageResponse(BaseSchema):
    id: UUID
    chat_id: UUID
    text: str
    role: MessageRole

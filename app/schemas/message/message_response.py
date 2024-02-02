import datetime
from uuid import UUID

from app.enums.message_enums import MessageRole
from app.schemas.base import BaseSchema


class MessageResponse(BaseSchema):
    id: UUID
    chat_id: UUID
    text: str
    role: MessageRole
    created_at: datetime.datetime
    follow_up_questions: str | None
    sql_query: str | None
    stored_file_id: str | None

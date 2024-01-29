from app.schemas.base import BaseSchema
from app.enums.message_enums import MessageRole
from uuid import UUID
import datetime

class MessageResponse(BaseSchema):
    id: UUID
    chat_id: UUID
    text: str
    role: MessageRole
    created_at: datetime.datetime
    follow_up_questions: str | None
    sql_query: str | None
    stored_file_id: str | None
    

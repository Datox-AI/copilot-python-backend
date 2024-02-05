import datetime
from uuid import UUID
from typing import List
from app.enums.message_enums import MessageRole
from app.schemas.base import BaseSchema


class AnalyticAgentMessageResponse(BaseSchema):
    id: UUID
    chat_id: UUID
    text: str
    role: MessageRole
    created_at: datetime.datetime
    follow_up_questions: str | None
    sql_query: str | None
    stored_file_id: str | None


class RAGAgentMessageResponse(BaseSchema):
    id: UUID
    chat_id: UUID
    text: str
    sources: List[str]
    role: MessageRole
    created_at: datetime.datetime
    # follow_up_questions: str | None
    

class UserMessageResponse(BaseSchema):
    id: UUID
    chat_id: UUID
    text: str
    role: MessageRole
    pinned: bool | None
    pinned_date: datetime.datetime | None
    reply_to: UUID | None
    questions: list[str] | None
    created_at: datetime.datetime

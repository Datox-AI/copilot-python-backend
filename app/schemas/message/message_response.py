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


class SharePointFilesResponse(BaseSchema):
    id: UUID
    item_name: str
    item_url: str
    content_type: str
    last_modified: datetime.datetime
    item_size: int


class RAGAgentMessageResponse(BaseSchema):
    id: UUID
    created_at: datetime.datetime
    chat_id: UUID
    text: str
    searched_files: List[SharePointFilesResponse]
    role: MessageRole
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

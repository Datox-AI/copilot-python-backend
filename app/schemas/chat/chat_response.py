from datetime import datetime
from uuid import UUID

from app.enums import ChatType
from app.schemas.base import BaseSchema
from app.schemas.message import AnalyticAgentMessageResponse


class ChatSnowflakeData(BaseSchema):
    id: UUID
    snowflake_account: str
    database_name: str
    snowflake_schema: str
    warehouse: str


class ChatResponse(BaseSchema):
    id: UUID
    name: str
    created: datetime
    pinned: bool
    pinned_date: datetime | None = None
    type: ChatType
    messages_count: int
    assistant_thread_id: str | None = None
    assistant_id: str | None = None
    
    files_count: int
    last_message: datetime | None = None
    snowflake_data: ChatSnowflakeData | None = None


class ChatHistoryResponse(BaseSchema):
    id: UUID
    name: str
    created: datetime
    type: ChatType
    snowflake_data: ChatSnowflakeData | None = None
    messages: list

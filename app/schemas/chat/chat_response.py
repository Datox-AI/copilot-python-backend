from app.schemas.base import BaseSchema
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID

from app.enums import ChatType
from app.schemas.message import MessageResponse


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
    pinned_date: Optional[datetime] = None
    type: ChatType
    messages_count: int
    files_count: int
    last_message: Optional[datetime] = None
    snowflake_data: Optional[ChatSnowflakeData] = None


class ChatHistoryResponse(BaseSchema):
    id: UUID
    name: str
    created: datetime
    type: ChatType
    snowflake_data: Optional[ChatSnowflakeData] = None
    messages: List[MessageResponse]

from app.schemas.base import BaseSchema
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.enums import ChatType


class AgentResponse(BaseSchema):
    final: str
    created: datetime
    pinned: bool
    pinned_date: Optional[datetime] = None
    type: ChatType
    messages_count: int
    files_count: int
    last_message: Optional[datetime] = None

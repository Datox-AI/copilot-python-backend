from contextvars import ContextVar
from typing import Optional
from uuid import UUID

current_user_id: ContextVar[Optional[UUID]] = ContextVar("current_user_id", default=None)

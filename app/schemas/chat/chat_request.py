from app.schemas.base import BaseSchema
from uuid import UUID

from app.enums import ChatType


class CreateChatRequest(BaseSchema):
    type: ChatType


class UpdateChatRequest(BaseSchema):
    id: UUID
    name: str
    pinned: bool

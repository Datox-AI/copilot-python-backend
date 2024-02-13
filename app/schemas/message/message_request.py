from uuid import UUID

from pydantic import BaseModel
from typing import Optional, List


class CreateMessageRequest(BaseModel):
    prompt: str
    replyTo: Optional[UUID] = None
    files: Optional[List[UUID]] = None


class UpdateMessageRequest(BaseModel):
    id: Optional[UUID] = None
    pinned: bool

    class Config:
        json_schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "pinned": True,
            }
        }


class DeleteMessagesRequest(BaseModel):
    ids: List[UUID]

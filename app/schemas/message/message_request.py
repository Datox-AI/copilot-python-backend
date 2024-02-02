from uuid import UUID

from pydantic import BaseModel


class CreateMessageRequest(BaseModel):
    prompt: str
    replyTo: UUID | None
    files: list[UUID] | None


class UpdateMessageRequest(BaseModel):
    id: UUID
    text: str | None = None
    pinned: bool | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "text": "Обновлённый текст сообщения",
                "pinned": True,
            }
        }

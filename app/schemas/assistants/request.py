from fastapi import UploadFile

from app.schemas.base import BaseSchema


class CreateAssistantSchema(BaseSchema):
    name: str
    description: str
    instruction: str


class UpdateAssistantSchema(BaseSchema):
    name: str | None = None
    description: str | None = None
    instruction: str | None = None


class CreateAssistantMessageSchema(BaseSchema):
    prompt: str
    file: UploadFile | None = None

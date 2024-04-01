from app.schemas.base import BaseSchema
from typing import Union, List
from fastapi import UploadFile


class CreateAssistantSchema(BaseSchema):
    name: str
    description: str
    instruction: Union[str]


class UpdateAssistantSchema(BaseSchema):
    name: str | None = None
    description: str | None = None
    instruction: Union[str] | None = None


class CreateAssistantMessageSchema(BaseSchema):
    prompt: str

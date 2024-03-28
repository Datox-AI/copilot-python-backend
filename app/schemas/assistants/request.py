from app.schemas.base import BaseSchema
from typing import Union, List
from fastapi import UploadFile

class CreateAssistantSchema(BaseSchema):
    name: str
    description: str
    instruction: Union[str]

class CreateAssistantMessageSchema(BaseSchema):
    prompt: str
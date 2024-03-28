from uuid import UUID
from typing import List
from app.schemas.base import BaseSchema


class AssistantKnowledgeFileSchema(BaseSchema):
    id: UUID
    name: str 
    type: str
    is_deleted: bool

class AssistantResponseSchema(BaseSchema):
    id: UUID
    name: str
    description: str
    instructions: str
    assistant_id: str
    icon_id: UUID | None = None
    knowledge_files: List[AssistantKnowledgeFileSchema]



        

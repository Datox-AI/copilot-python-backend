from uuid import UUID
from typing import List
from app.schemas.base import BaseSchema


class AssistantKnowledgeFileSchema(BaseSchema):
    id: UUID
    name: str 
    type: str
    blob_name: str | None = None

class AssistantResponseSchema(BaseSchema):
    id: UUID
    name: str
    description: str
    instructions: str
    assistant_id: str
    icon_file_path: str | None = None
    knowledge_files: List[AssistantKnowledgeFileSchema]



        

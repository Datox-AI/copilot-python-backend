from datetime import datetime
from typing import List

from app.models.maindb.assistants import Assistant, AssistantFile
from app.schemas.assistants.response import AssistantResponseSchema, AssistantKnowledgeFileSchema


class AssistantMapper:
    @staticmethod
    def map_to_assistant_response(
        assistant: Assistant,
        knowledge_file_objs: List[AssistantFile]
    ):
        knowledge_file_objs.sort(key=lambda file_obj: file_obj.created_at)
        knowledge_file_objs = [file_obj for file_obj in knowledge_file_objs if not file_obj.is_deleted]
        
        knowledge_file_responses = [
            AssistantMapper.map_to_assistant_file_response(knowledge_file=knowledge_file) 
            for knowledge_file in knowledge_file_objs
        ]
        return AssistantResponseSchema(
            id=assistant.id,
            assistant_id=assistant.assistant_id,
            icon_id=assistant.icon_id,
            name=assistant.name,
            description=assistant.description,
            instructions=assistant.instructions,
            knowledge_files=knowledge_file_responses
        )
        
        
    @staticmethod
    def map_to_assistant_file_response(
        knowledge_file: AssistantFile
    ):
        return AssistantKnowledgeFileSchema(
            id=knowledge_file.id,
            name=knowledge_file.name,
            type=knowledge_file.type,
            is_deleted=knowledge_file.is_deleted   
        )
        
    @staticmethod
    def map_to_assistant_chats_response(
        assistant: Assistant
    ):
        knowledge_file_objs = assistant.knowledge_files
        knowledge_file_objs.sort(key=lambda file_obj: file_obj.created_at)
        knowledge_file_objs = [file_obj for file_obj in knowledge_file_objs if not file_obj.is_deleted]
         
        knowledge_files = [AssistantMapper.map_to_assistant_file_response(knowledge_file) for knowledge_file in knowledge_file_objs]
        return AssistantResponseSchema(
            id=assistant.id,
            assistant_id=assistant.assistant_id,
            icon_id=assistant.icon_id,
            name=assistant.name,
            description=assistant.description,
            instructions=assistant.instructions,
            knowledge_files=knowledge_files
        )
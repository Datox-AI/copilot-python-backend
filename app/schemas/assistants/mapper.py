import os 
from datetime import datetime
from typing import List

from app.models.maindb.assistants import Assistant, AssistantFile
from app.schemas.assistants.response import AssistantResponseSchema, AssistantKnowledgeFileSchema
from app.const import STATIC_FILES_DESTINATION

class AssistantMapper:
    @staticmethod
    def map_to_assistant_response(
        assistant: Assistant,
        request_url: str
    ):
        # request_url = "request_url"
        knowledge_file_objs = assistant.knowledge_files
        knowledge_file_objs.sort(key=lambda file_obj: file_obj.created_at)
        knowledge_file_objs = [file_obj for file_obj in knowledge_file_objs if not file_obj.is_deleted]
        
        knowledge_file_responses = [
            AssistantMapper.map_to_assistant_file_response(knowledge_file=knowledge_file) 
            for knowledge_file in knowledge_file_objs
        ]
        if assistant.icon_file_name:   
            icon_file_api_path = f"{request_url}/{assistant.icon_file_name}"
        else:
            icon_file_api_path = None
        return AssistantResponseSchema(
            id=assistant.id,
            assistant_id=assistant.assistant_id,
            icon_file_path=icon_file_api_path,
            name=assistant.name,
            description=assistant.description,
            instructions=assistant.instructions,
            knowledge_files=knowledge_file_responses
        )
        
        
    @staticmethod
    def map_to_assistant_file_response(
        knowledge_file: AssistantFile,
    ):
        return AssistantKnowledgeFileSchema(
            id=knowledge_file.id,
            name=knowledge_file.name,
            type=knowledge_file.type,
            blob_name=knowledge_file.blob_name   
        )
        
    @staticmethod
    def map_to_assistant_chats_response(
        assistant: Assistant
    ):
        # knowledge_file_objs = assistant.knowledge_files
        # knowledge_file_objs.sort(key=lambda file_obj: file_obj.created_at)
        # knowledge_file_objs = [file_obj for file_obj in knowledge_file_objs if not file_obj.is_deleted]
         
        # knowledge_files = [AssistantMapper.map_to_assistant_file_response(knowledge_file) for knowledge_file in knowledge_file_objs]
        # return AssistantResponseSchema(
        #     id=assistant.id,
        #     assistant_id=assistant.assistant_id,
        #     icon_id=assistant.icon_id,
        #     name=assistant.name,
        #     description=assistant.description,
        #     instructions=assistant.instructions,
        #     knowledge_files=knowledge_files
        # )
        pass 
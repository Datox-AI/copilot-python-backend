import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from openai import AzureOpenAI
from langchain.agents.openai_assistant import OpenAIAssistantRunnable
from app.backend.session import create_maindb_session
from app.models.maindb import Assistant, AssistantFile
from app.shared.auth.azure_scheme import current_user
from app.schemas.identity.current_user import CurrentUser
from app.schemas.assistants import CreateAssistantSchema, AssistantMapper
from app.services.files.azure_index_manager import AzureSearchIndexManager
from app.services.messages.user_message_services import MIME_TYPE_MAP

load_dotenv()

class AssistantService:
    def __init__(
        self,
        user: Annotated[CurrentUser, Depends(current_user)],
        session: Annotated[Session, Depends(create_maindb_session)],
    ):
        self.user = user 
        self.session = session
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.environ.get("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("GPT4_TURBO_OPENAI_API_VERSION"),
        )
        assistants_index_name = os.environ.get("AZURE_COGNITIVE_SEARCH_ASSISTANTS_INDEX_NAME")
        self.azure_indexer = AzureSearchIndexManager(
            user=user, 
            session=session, 
            chat_id=self.chat_id,
            index_name=assistants_index_name
        )
        
        
    def create_assistant(self, request: CreateAssistantSchema):
        try:
            # I am using langchain's wrapper since it also supports converting custom tool into openai function
            agent = OpenAIAssistantRunnable.create_assistant(
                name=request.name,
                instructions=request.instruction,
                model="gpt-35-turbo-16k",
                as_agent=True
            )
        except Exception as e:
            raise HTTPException(f"Assistant create function failed: {e}", status_code=500)

        assistant_id = agent.assistant_id
        uploaded_files = request.knowledge_files
        # uploading files to azure index
        for uploaded_file in uploaded_files:
            file_id = uuid.uuid4()
            file_name = uploaded_file.filename
            file_content = uploaded_file.read()
            file_extension = uploaded_file.content_type
            file_type = MIME_TYPE_MAP.get(file_extension, "unknown")
            self.azure_indexer.process_and_store_texts_for_assistant_index(
                file_id=file_id,
                file_content=file_content,
                file_type=file_type,
                file_name=file_name,
                assistant_id=assistant_id,
            )
        # saving objects to database 
        assistant_obj = Assistant(
            name=request.name,
            description=request.description,
            instruction=request.instruction,
            assistant_id=assistant_id
        )
        assistant_knowledge_files = []
        for uploaded_file in uploaded_files:
            knowledge_file_obj = AssistantFile(
                id=file_id,
                name=uploaded_file.name,
                type=uploaded_file.content_type,
                is_deleted=False,
                assistant_id=assistant_id,
                assistant=assistant_obj,
            )
            assistant_knowledge_files.append(knowledge_file_obj)
        
        self.session.add(assistant_obj)
        self.session.add_all(assistant_knowledge_files)
        self.session.commit()
        
        return AssistantMapper.map_to_assistant_response(
            assistant=assistant_obj, assistant_knowledge_files=assistant_knowledge_files
        )
        
        
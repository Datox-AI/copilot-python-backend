import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List
from uuid import UUID

from fastapi import Depends, HTTPException, UploadFile, Response
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


load_dotenv(override=True)


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
            api_version=os.environ.get("GPT4_ASSISTANT_OPENAI_API_VERSION"),
        )
        assistants_index_name = os.environ.get("AZURE_COGNITIVE_SEARCH_ASSISTANTS_INDEX_NAME")
        self.azure_indexer = AzureSearchIndexManager(
            user=user, 
            session=session, 
            index_name=assistants_index_name
        )
    
    async def create_assistant(self, request: CreateAssistantSchema, knowledge_files: List[UploadFile]):
        print("request---- ", request)
        try:
            
            openai_assistant = self.openai_client.beta.assistants.create(
                instructions=request.instruction,
                name=request.name,
                tools=[
                    {
                        "type": "function",
                        "function":{
                            "name": "get_documents",
                            "description": "get_documents(prompt: str) - Use this tool to get relevant documents",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                "prompt": {}
                            },
                            "required": [
                            "prompt"
                            ]
                        }
                        }
                    }
                ],
                model="gpt-35-turbo-16k",
            )
                
        except Exception as e:
            raise HTTPException(detail=f"Assistant create function failed: {e}", status_code=500)

        assistant_id = openai_assistant.id
        try:    
            # uploading files to azure index'
            file_ids = []
            for uploaded_file in knowledge_files:
                file_id = uuid.uuid4()
                file_ids.append(file_id)
                file_name = uploaded_file.filename
                file_content = await uploaded_file.read()
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
                instructions=request.instruction,
                assistant_id=assistant_id
            )
            knowledge_file_objs = []
            for file_id, uploaded_file in zip(file_ids, knowledge_files):
                knowledge_file_obj = AssistantFile(
                    id=file_id,
                    created_at=datetime.now(),
                    name=uploaded_file.filename,
                    type=uploaded_file.content_type,
                    is_deleted=False,
                    assistant_id=assistant_id,
                    assistant=assistant_obj,
                )
                knowledge_file_objs.append(knowledge_file_obj)
            
            self.session.add(assistant_obj)
            self.session.add_all(knowledge_file_objs)
            self.session.commit()
            
            return AssistantMapper.map_to_assistant_response(
                assistant=assistant_obj, knowledge_file_objs=knowledge_file_objs
            )
        
        except Exception as e:
            # deleting assistant if any error occurs
            self.openai_client.beta.assistants.delete(assistant_id=assistant_id)
            print("deleted assistant")
            # raise e
            raise HTTPException(detail=f"Assistant creation failed: {e}", status_code=500)
            
            
    def get_assistants(self):
        assistants = self.session.query(Assistant).filter(
            Assistant.created_by==self.user.user_id, Assistant.is_deleted == False
        ).all()
        return [
            AssistantMapper.map_to_assistant_response(
                assistant=assistant,
                knowledge_file_objs=assistant.knowledge_files  
            ) 
            for assistant in assistants
        ]
        
    def get_assistant_chats(self, assistant_id: str):
        assistant = self.session.query(Assistant).filter(
            Assistant.assistant_id==assistant_id, Assistant.is_deleted == False
        ).first()
        if assistant:
            if assistant.created_by != self.user.user_id:
                raise HTTPException(status_code=403, detail="You are not authorized to view this assistant")
            return AssistantMapper.map_to_assistant_chats_response(assistant=assistant)
        return Response(status_code=404, content="Assistant not found")
    
    
    async def update_assistant_files(self, assistant_id: str, files_to_delete: List[str], new_files: List[UploadFile]):
        assistant_obj = self.session.query(Assistant).filter(
            Assistant.assistant_id==assistant_id,
            Assistant.created_by==self.user.user_id,
            Assistant.is_deleted == False
            ).first()
        if assistant_obj is not None:
            # deleting files
            print(datetime.now(), " -before deleting files")
            for file_id in files_to_delete:
                file_obj = self.session.query(AssistantFile).filter(AssistantFile.id==file_id).first()
                if file_obj:
                    file_obj.is_deleted = True                
                    # self.azure_indexer.delete_document(file_id=file_id)
            print(datetime.now(), " -after deleting files")
            # adding new files
            knowledge_file_objs = []
            for uploaded_file in new_files:
                file_id = uuid.uuid4()
                file_name = uploaded_file.filename
                file_content = await uploaded_file.read()
                file_extension = uploaded_file.content_type
                file_type = MIME_TYPE_MAP.get(file_extension, "unknown")
                bef = datetime.now()
                
                self.azure_indexer.process_and_store_texts_for_assistant_index(
                    file_id=file_id,
                    file_content=file_content,
                    file_type=file_type,
                    file_name=file_name,
                    assistant_id=assistant_id,
                )
                aft = datetime.now()
                print((aft - bef).seconds, " ---seconds for whole file upload")
                
                knowledge_file_obj = AssistantFile(
                    id=file_id,
                    created_at=datetime.now(),
                    name=uploaded_file.filename,
                    type=uploaded_file.content_type,
                    is_deleted=False,
                    assistant_id=assistant_id,
                    assistant=assistant_obj,
                )
                knowledge_file_objs.append(knowledge_file_obj)
                
            self.session.add_all(knowledge_file_objs)
            self.session.commit()
            return AssistantMapper.map_to_assistant_response(
                assistant=assistant_obj, knowledge_file_objs=assistant_obj.knowledge_files
            )        
        raise HTTPException(status_code=404, detail="Assistant not found")
            
            
            
    def delete_assistant(self, assistant_id):
        assistant_obj = self.session.query(Assistant).filter(
            Assistant.assistant_id==assistant_id,
            Assistant.created_by==self.user.user_id,
            Assistant.is_deleted == False
            ).first()
        if assistant_obj:
            try:
                self.openai_client.beta.assistants.delete(assistant_id=assistant_id)
            except:
                pass 
            
            # Mark the assistant and its chats as deleted
            chat_objs = assistant_obj.chats
            for chat_obj in chat_objs:
                chat_obj.is_deleted = True
                assistant_obj.deleted_at = datetime.now()
                assistant_obj.deleted_by = self.user.user_id    
            assistant_obj.is_deleted = True
            assistant_obj.deleted_at = datetime.now()
            assistant_obj.deleted_by = self.user.user_id
            self.session.commit()     
            return Response(status_code=204)
        raise HTTPException(status_code=404, detail="Assistant not found")   
        
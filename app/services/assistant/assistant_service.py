import uuid
import os
import asyncio
from datetime import datetime
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
from app.schemas.assistants import CreateAssistantSchema, AssistantMapper, UpdateAssistantSchema
from app.services.files.azure_index_manager import AzureSearchIndexManager
from app.services.messages.user_message_services import MIME_TYPE_MAP
from app.infrastructure.analytics_agent.azure_storage_manager import AzureBlobStorageManager, AzureAsyncBlobStorageManager
from app.infrastructure.assistants.prompt import ASSISTANT_INSTRUCTION_TEMPLATE


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
        self.async_blob_storage_manager = AzureAsyncBlobStorageManager(
            container_name=os.environ["AZURE_STORAGE_ASSISTANT_FILE_CONTAINER"]
        )

    
    async def create_assistant(self, request: CreateAssistantSchema, knowledge_files: List[UploadFile], icon: UploadFile = None): 
        try:
            instructions = ASSISTANT_INSTRUCTION_TEMPLATE.format(user_instruction=request.instruction)
            openai_assistant = self.openai_client.beta.assistants.create(
                instructions=instructions,
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

        # uploading icon
        icon_file_id = await self.async_blob_storage_manager.upload_file(file=icon)
        #uploading files to azure index
        assistant_id = openai_assistant.id
        try:    
            file_ids = []
            file_contents = []
            for uploaded_file in knowledge_files:
                file_id = uuid.uuid4()
                file_ids.append(file_id)
                file_name = uploaded_file.filename
                file_content = await uploaded_file.read()
                file_contents.append(file_content)
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
                assistant_id=assistant_id,
                icon_id=icon_file_id
            )
            upload_tasks = [
                self.async_blob_storage_manager.save_and_upload_assistant_file(
                    file_id=str(file_id), 
                    file_content=file_content,
                    session=self.session, 
                    uploaded_file=uploaded_file, 
                    assistant_obj=assistant_obj
                ) for uploaded_file, file_id, file_content in zip(knowledge_files, file_ids, file_contents)
                ]
            await asyncio.gather(*upload_tasks)
            await self.async_blob_storage_manager.close()
            
            self.session.add(assistant_obj)
            self.session.commit()
            return AssistantMapper.map_to_assistant_response(assistant=assistant_obj)
        
        except Exception as e:
            # deleting assistant if any error occurs
            self.openai_client.beta.assistants.delete(assistant_id=assistant_id)
            print("deleted assistant")
            # raise e
            raise HTTPException(detail=f"Assistant creation failed: {e}", status_code=500)
            

    async def update_assistant_files(self, assistant_id: str, files_to_delete: List[str], new_files: List[UploadFile]):
        assistant_obj = self.session.query(Assistant).filter(
            Assistant.assistant_id==assistant_id,
            Assistant.created_by==self.user.user_id,
            Assistant.is_deleted == False
            ).first()
        if assistant_obj is not None:
            # deleting files
            for file_id in files_to_delete:
                file_obj = self.session.query(AssistantFile).filter(AssistantFile.id==file_id).first()
                if file_obj:
                    file_obj.is_deleted = True                
                    # self.azure_indexer.delete_document(file_id=file_id)
            # adding new files
            file_ids = []
            file_contents = []
            for uploaded_file in new_files:
                file_id = uuid.uuid4()
                file_ids.append(file_id)
                file_name = uploaded_file.filename
                file_content = await uploaded_file.read()
                file_contents.append(file_content)
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

            upload_tasks = [
                self.async_blob_storage_manager.save_and_upload_assistant_file(
                    file_id=str(file_id), 
                    file_content=file_content,
                    session=self.session, 
                    uploaded_file=uploaded_file, 
                    assistant_obj=assistant_obj
                ) for uploaded_file, file_id, file_content in zip(new_files, file_ids, file_contents)
                ]
            await asyncio.gather(*upload_tasks)
            await self.async_blob_storage_manager.close()   
                
            self.session.commit()
            return AssistantMapper.map_to_assistant_response(assistant=assistant_obj)        
        raise HTTPException(status_code=404, detail="Assistant not found")
            
    async def update_assistant(
        self, 
        assistant_id: str, 
        request: UpdateAssistantSchema, 
        icon: UploadFile = None
        ):
        assistant_obj = self.session.query(Assistant).filter(
            Assistant.assistant_id==assistant_id,
            Assistant.created_by==self.user.user_id,
            Assistant.is_deleted == False
            ).first()
        if assistant_obj is not None:
            
            assistant_obj.name = request.name if request.name is not None else assistant_obj.name
            assistant_obj.description = request.description if request.description is not None else assistant_obj.description
            assistant_obj.instructions = request.instruction if request.instruction is not None else assistant_obj.instructions
            res = self.openai_client.beta.assistants.update(
                assistant_id=assistant_id,
                instructions=assistant_obj.instructions,
                name=assistant_obj.name
            )
            print(res)
            if icon:
                icon_id = await self.async_blob_storage_manager.upload_file(file=icon)
                assistant_obj.icon_id = icon_id
                await self.async_blob_storage_manager.close()   
            
            self.session.commit()
            return AssistantMapper.map_to_assistant_response(assistant=assistant_obj)
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
             

    def get_assistants(self):
        assistants = self.session.query(Assistant).filter(
            Assistant.created_by==self.user.user_id, Assistant.is_deleted == False
        ).all()
        return [
            AssistantMapper.map_to_assistant_response(assistant=assistant) 
            for assistant in assistants
        ]
        
    def get_assistant(self, assistant_id: str):
        assistant = self.session.query(Assistant).filter(
            Assistant.assistant_id==assistant_id, Assistant.is_deleted == False
        ).first()
        if assistant:
            if assistant.created_by != self.user.user_id:
                raise HTTPException(status_code=403, detail="You are not authorized to view this assistant")
            return AssistantMapper.map_to_assistant_response(assistant=assistant)
        raise HTTPException(status_code=404, content="Assistant not found") 
    
    
    async def download_icon(self, icon_id: str):
        stream, media_type = await self.async_blob_storage_manager.download_file(file_id=icon_id)
        await self.async_blob_storage_manager.close()   
        return stream, media_type
        
    async def download_knowledge_file(self, assistant_id: str, knowledge_blob_name: str):
        assistant = self.session.query(Assistant).filter(
            Assistant.assistant_id==assistant_id, Assistant.is_deleted == False
        ).first()
        if assistant:
            if assistant.created_by != self.user.user_id:
                raise HTTPException(status_code=403, detail="You are not authorized to view this assistant")
            knowledge_file = self.session.query(AssistantFile).filter(
                AssistantFile.blob_name==knowledge_blob_name
            ).first()
            if knowledge_file is None:
                raise HTTPException(status_code=404, detail="Knowledge file not found")
            if "." in knowledge_blob_name:
                knowledge_blob_name = knowledge_blob_name.split(".")[0]
            stream, media_type = await self.async_blob_storage_manager.download_file(file_id=knowledge_blob_name)
            await self.async_blob_storage_manager.close()
            return stream, media_type
        raise HTTPException(status_code=404, detail="Assistant not found")
            
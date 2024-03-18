import json
import asyncio
import shutil
import tempfile
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.enums.message_enums import MessageRole, MessageStatus
from app.infrastructure.ChatGPT_assistant.agent_service import ChatGPTAssistant
from app.models.maindb import Chat, Message
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.schemas.message.message_request import CreateMessageRequest, UpdateMessageRequest
from app.infrastructure.analytics_agent.azure_storage_manager import AzureAsyncBlobStorageManager
from app.services.files.azure_index_manager import AzureSearchIndexManager
from app.services.files.user_files_services import UserFileService, save_file_id_to_db
from app.shared.auth.azure_scheme import current_user
import aiofiles
from .message_create_stream import OpenAIChatStream

MIME_TYPE_MAP = {
    'application/pdf': 'pdf',
    'text/csv': 'csv',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.ms-powerpoint': 'ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'text/plain': 'txt',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/msword': 'doc',
}

load_dotenv()

class UserMessageService:
    def __init__(
        self,
        user: Annotated[CurrentUser, Depends(current_user)],
        chat_id: UUID,
        session: Annotated[Session, Depends(create_maindb_session)],
    ) -> None:
        self.session = session
        self.user = user
        self.chat_id = chat_id
        self.streamer = OpenAIChatStream()
        self.file_service = UserFileService(session, user)
        self.async_blob_service = AzureAsyncBlobStorageManager(os.environ["AZURE_STORAGE_FILE_CONTAINER"])
        self.azure_indexer = AzureSearchIndexManager(user=user, session=session, chat_id=self.chat_id)
        thread_id = self._get_thread_id()
        self.chatgpt_assistant = ChatGPTAssistant(thread_id=thread_id)

    def _get_thread_id(self):
        chat_obj = self.session.query(Chat).filter(Chat.id == self.chat_id).first()
        return chat_obj.assistant_thread_id

    def _update_thread_id(self, thread_id: str):
        print("updating, --- ", thread_id)

        chat_obj = self.session.query(Chat).filter(Chat.id == self.chat_id).first()
        if not chat_obj.assistant_thread_id:
            print("chat doesnt have id")
            chat_obj.assistant_thread_id = thread_id
            self.session.commit()

    async def create_message(self, request: CreateMessageRequest):
        self._check_chat_exists(chat_id=self.chat_id)
        reply_message = None
        if request.replyTo:
            reply_message = self.session.query(Message).filter(Message.id == request.replyTo).first()
            if not reply_message:
                raise HTTPException(
                    status_code=404, detail=f"Message object under {request.replyTo} id does not exist"
                )
        new_user_message = Message(
            id=uuid.uuid4(),
            chat_id=self.chat_id,
            text=request.prompt,
            status=MessageStatus.Success,
            role=MessageRole.User,
            reply_to_id=request.replyTo if request.replyTo else None,
        )
        self.session.add(new_user_message)
        self.session.commit()
        uploaded_file_ids = None
        file_context = None
        if request.files:
            uploaded_file_ids = [str(uuid.uuid4()) for _ in request.files]
            for file_id, upload_file in zip(uploaded_file_ids, request.files):
                content = await upload_file.read()
                file_extension = upload_file.content_type
                file_type = MIME_TYPE_MAP.get(file_extension, "unknown")
                self.azure_indexer.process_and_store_texts(content, file_id, file_type)
                await upload_file.seek(0)
            upload_tasks = [self.async_blob_service.save_and_upload_file(self.session, upload_file, file_id) for upload_file, file_id in zip(request.files, uploaded_file_ids)]
            await asyncio.gather(*upload_tasks)
            await self.async_blob_service.close()
            print(uploaded_file_ids)
            file_context = self.azure_indexer.search_documents(
                prompt=request.prompt, 
                file_ids=uploaded_file_ids,
                chat_id=self.chat_id,
            )
    
        assistant_response = self.chatgpt_assistant.execute_agent(
            user_input=request.prompt, 
            user_id=self.user.user_id, 
            chat_id=self.chat_id,
            file_context=file_context
        )
        if type(assistant_response) == dict:
            thread_id = assistant_response["thread_id"]
            self._update_thread_id(thread_id=thread_id)
            # saving response
            new_assistant_message = Message(
                id=uuid.uuid4(),
                chat_id=self.chat_id,
                text=assistant_response["output"],
                follow_up_questions=assistant_response["followup_questions"],
                status=MessageStatus.Success,
                role=MessageRole.Assistant,
                prompt_id=new_user_message.id,
            )
            self.session.add(new_assistant_message)
            self.session.commit()
            return MessageMapper.map_to_user_message_response(message=new_assistant_message)

        else:
            raise HTTPException(status_code=500, detail=assistant_response)

    async def save_temp_file(self, upload_file: UploadFile):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload_file.filename).suffix) as temp_file:
                shutil.copyfileobj(upload_file.file, temp_file)
                temp_file_path = temp_file.name
                file_extension = upload_file.content_type  # Используем MIME тип как "расширение"
        finally:
            upload_file.file.close()
        return temp_file_path, file_extension

    def get_messages(self, chat_id: UUID):
        self._check_chat_exists(chat_id=self.chat_id)
        message_objs = (
            self.session.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        )

        return [MessageMapper.map_to_user_message_response(message_obj) for message_obj in message_objs]

    def delete_message(self, chat_id: UUID, message_id: UUID):
        message = self.session.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
        if message:
            self.session.delete(message)
            self.session.commit()
            return True
        return False

    def update_message(self, chat_id: UUID, message_id: UUID, updated_data: UpdateMessageRequest):
        message_obj = self.session.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
        if message_obj:
            if message_obj.id != updated_data.id:
                raise HTTPException(status_code=400, detail=f"Message id you provided ({message_id}) is wrong")
            message_obj.pinned = updated_data.pinned
            if message_obj.pinned:
                message_obj.pinned_date = datetime.now()
            self.session.commit()

            return message_obj
        else:
            raise HTTPException(status_code=404, detail="Message not found")

    def delete_messages_batch(self, chat_id: UUID, message_ids: list):
        self.session.query(Message).filter(Message.id.in_(message_ids), Message.chat_id == chat_id).delete(
            synchronize_session=False
        )
        self.session.commit()

    def _check_chat_exists(self, chat_id: UUID) -> bool:
        self.chat_obj = self.session.query(Chat).filter(Chat.id == chat_id).first()
        if not self.chat_obj:
            raise HTTPException(status_code=404, detail=f"Chat object under {chat_id} id does not exist")
        if self.chat_obj.type != ChatType.Analytics:
            raise HTTPException(
                status_code=400, detail=f"Chat object under {chat_id} id does not have Analytics as its chat type"
            )

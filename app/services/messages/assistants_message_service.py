import os
import uuid
from datetime import datetime
from typing import Annotated
from uuid import UUID

import tiktoken
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.enums.message_enums import MessageRole, MessageStatus
from app.infrastructure.analytics_agent.azure_storage_manager import AzureAsyncBlobStorageManager
from app.infrastructure.assistants.assistant_service import AssistantAgent
from app.infrastructure.assistants.prompt import ASSISTANT_MESSAGE_WITH_FILE_TEMPLATE
from app.models.maindb import Assistant, AssistantFile, Chat, Message, MessageAssistantDocument, MessageFile
from app.schemas.assistants import CreateAssistantMessageSchema
from app.schemas.chat import ChatMapper
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.services.files.text_processor import TextProcessor
from app.services.messages.user_message_services import MIME_TYPE_MAP
from app.shared.auth.azure_scheme import current_user

enc = tiktoken.get_encoding("cl100k_base")


class AssistantMessageService:
    MAX_TOKEN_LIMIT_FOR_UPLOADED_FILE = 10000

    def __init__(
        self,
        assistant_id: str,
        chat_id: UUID,
        user: Annotated[CurrentUser, Depends(current_user)],
        session: Annotated[Session, Depends(create_maindb_session)],
    ) -> None:
        self.session = session
        self.user = user
        # checking IDs
        self._check_assistant_id(assistant_id=assistant_id)
        self.assistant_id = assistant_id

        self._check_chat_id(
            chat_id=chat_id,
        )
        self.chat_id = chat_id

    def _check_chat_id(self, chat_id):
        self.chat_obj = (
            self.session.query(Chat)
            .filter(Chat.id == chat_id, Chat.created_by == self.user.user_id, Chat.is_deleted == False)
            .first()
        )
        if not self.chat_obj:
            raise HTTPException(status_code=404, detail=f"Chat object under {chat_id} id does not exist")
        elif self.chat_obj.type != ChatType.Assistant:
            raise HTTPException(
                status_code=400, detail=f"Chat object under {chat_id} id does not have Assistant as its chat type"
            )
        print(self.chat_obj.assistant.assistant_id, " ---assistant id")
        print(self.assistant_id, " ---assistant id")
        if self.chat_obj.assistant.assistant_id != self.assistant_id:
            raise HTTPException(
                status_code=400,
                detail=f"Chat object under {chat_id} id does not have {self.assistant_id} as its assistant id",
            )

    def _check_assistant_id(self, assistant_id):
        self.assistant_obj = (
            self.session.query(Assistant)
            .filter(Assistant.assistant_id == assistant_id, Assistant.created_by == self.user.user_id)
            .first()
        )
        if not self.assistant_obj:
            raise HTTPException(status_code=404, detail=f"Assistant object under {assistant_id} id does not exist")

    async def create_user_message(
        self,
        request: CreateAssistantMessageSchema,
    ):
        prompt = request.prompt
        new_user_message = Message(
            id=uuid.uuid4(),
            created_at=datetime.now(),
            chat_id=self.chat_id,
            text=prompt,
            status=MessageStatus.Success,
            role=MessageRole.User,
        )
        if request.file:
            file_id = str(uuid.uuid4())
            file_content_in_bytes = await request.file.read()
            file_extension = request.file.content_type
            file_name = request.file.filename
            file_type = MIME_TYPE_MAP.get(file_extension, "unknown")
            # extracting file content to text
            text_processor = TextProcessor()
            try:
                extracted_texts = text_processor.extract_texts(data=file_content_in_bytes, file_type=file_type)
            except ValueError as ve:
                print(f"Error while extracting text from file: {ve}")
                raise HTTPException(status_code=400, detail=ve.args[0])
            print(len(extracted_texts), " len of extracted texts")
            extracted_added_text = "".join(extracted_texts)
            token_of_file = len(enc.encode(extracted_added_text))
            if token_of_file > self.MAX_TOKEN_LIMIT_FOR_UPLOADED_FILE:
                raise HTTPException(status_code=400, detail="Uploaded file is too large")
            # changing the user input with file context
            user_input = ASSISTANT_MESSAGE_WITH_FILE_TEMPLATE.format(
                user_message=prompt, file_name=file_name, file_content=extracted_added_text
            )
            print(user_input, " user input ")
            print(token_of_file, " ---tokenss")
            # uploading file to azure storage
            async_azure_blob_storage_client = AzureAsyncBlobStorageManager(
                container_name=os.environ["AZURE_STORAGE_FILE_CONTAINER"]
            )
            await async_azure_blob_storage_client.save_and_upload_file(
                session=self.session, file=request.file, file_id=str(file_id), file_content=file_content_in_bytes
            )
            # saving to model object
            new_message_file = MessageFile(
                message_id=new_user_message.id, file_id=file_id, content=None, token=token_of_file
            )
            self.session.add(new_message_file)
        # assistant servicev
        knowledge_files_ids = [obj.id for obj in self.assistant_obj.knowledge_files]
        thread_id = self.chat_obj.assistant_thread_id
        assistant_agent_service = AssistantAgent(assistant_id=self.assistant_id, thread_id=thread_id)

        assistant_result = assistant_agent_service.execute_agent(
            user_input=user_input, knowledge_files_ids=knowledge_files_ids
        )
        new_agent_message = Message(
            id=uuid.uuid4(),
            chat_id=self.chat_id,
            created_at=datetime.now(),
            text=assistant_result["output"],
            status=MessageStatus.Success,
            role=MessageRole.Assistant,
        )
        print(thread_id, " ---thread id")
        relevant_docs = assistant_result["relevant_docs"]
        for doc in relevant_docs:
            print(doc["fileName"], " ---doc name")
        print(len(relevant_docs), " ---relavant docs")

        assistant_message_document_objs = []
        for document_metadata in relevant_docs:
            assistant_file_obj = (
                self.session.query(AssistantFile).filter(AssistantFile.id == document_metadata["fileId"]).first()
            )
            if assistant_file_obj:
                asst_message_document_obj = MessageAssistantDocument(
                    document_id=document_metadata["id"], message=new_agent_message, assistant_file=assistant_file_obj
                )
                assistant_message_document_objs.append(asst_message_document_obj)
            else:
                print(document_metadata["fileId"], " file not found")

        self.session.add(new_agent_message)
        self.session.add(new_user_message)
        self.session.add_all(assistant_message_document_objs)
        self.session.commit()
        return MessageMapper.map_to_assistant_message_response(new_agent_message)

    def get_messages(self):
        message_objs = (
            self.session.query(Message).filter(Message.chat_id == self.chat_id).order_by(Message.created_at.asc())
        )

        return ChatMapper.map_to_assistant_chat_history_response(chat=self.chat_obj, messages=message_objs)

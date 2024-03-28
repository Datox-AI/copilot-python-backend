import uuid
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.enums.message_enums import MessageRole, MessageStatus
from app.infrastructure.assistants.assistant_service import AssistantAgent
from app.models.maindb import Chat, Assistant, Message, MessageSharepointDocument
from app.schemas.chat import ChatMapper
from app.schemas.assistants import CreateAssistantMessageSchema   
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user
from app.schemas.message import MessageMapper


class AssistantMessageService:
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
        
        self._check_chat_id(chat_id=chat_id,)
        self.chat_id = chat_id

    def _check_chat_id(self, chat_id):
        self.chat_obj = self.session.query(Chat).filter(Chat.id == chat_id, Chat.created_by == self.user.user_id).first()
        if not self.chat_obj:
            raise HTTPException(status_code=404, detail=f"Chat object under {chat_id} id does not exist")
        if self.chat_obj.type != ChatType.FileSearch:
            raise HTTPException(
                status_code=400, detail=f"Chat object under {chat_id} id does not have FileSearch as its chat type"
            )
        if self.chat_obj.assistant_id != self.assistant_id:
            raise HTTPException(
                status_code=400, detail=f"Chat object under {chat_id} id does not have {self.assistant_id} as its assistant id"
            )   
    
    def _check_assistant_id(self, assistant_id):
        self.assistant_obj = self.session.query(Assistant).filter(Assistant.id == assistant_id, Assistant.created_by == self.user.user_id).first()
        if not self.assistant_obj:
            raise HTTPException(status_code=404, detail=f"Assistant object under {assistant_id} id does not exist")
        
        
    def create_user_message(
        self,
        request: CreateAssistantMessageSchema,
    ):
        prompt = request.prompt
        new_user_message = Message(
            id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            chat_id=self.chat_id,
            text=prompt,
            status=MessageStatus.Success,
            role=MessageRole.User,
        )
        knowledge_file_ids = [obj.id for obj in self.assistant_obj.knowledge_files]
        # assistant service
        thread_id = self.chat_obj.assistant_thread_id
        assistant_agent_service = AssistantAgent(assistant_id=self.assistant_id, thread_id=thread_id)
        
        result = assistant_agent_service.execute_agent(
            user_input=prompt,
            knowledge_files_ids=knowledge_file_ids
        )
        output = result['output']
        thread_id = result['thread_id']
        relevant_docs = result['relevant_docs']
        for doc in relevant_docs:
            print(doc["fileName"], " ---doc name")
        print(len(relevant_docs), " ---relavant docs")

        new_agent_message = Message(
            id=uuid.uuid4(),
            chat_id=self.chat_id,
            created_at=datetime.now(timezone.utc),
            text=output,
            status=MessageStatus.Success,
            role=MessageRole.Assistant,
        )
        # sharepoint_document_objs = []
        # for document_metadata in relevant_docs:
        #     sharepoint_document_obj = MessageSharepointDocument(
        #         document_id=document_metadata["id"],
        #         item_name=document_metadata["metadata_spo_item_name"],
        #         item_path=document_metadata["metadata_spo_item_path"],
        #         item_url=document_metadata["metadata_spo_item_weburi"],
        #         content_type=document_metadata["metadata_spo_item_content_type"],
        #         last_modified=document_metadata["metadata_spo_item_last_modified"],
        #         item_size=document_metadata["metadata_spo_item_size"],
        #         message=new_agent_message,
        #     )
        #     sharepoint_document_objs.append(sharepoint_document_obj)
        self.session.add(new_agent_message)
        self.session.add(new_user_message)
        self.session.commit()

        return MessageMapper.map_to_user_message_response(new_agent_message)

    def get_messages(self):
        message_objs = (
            self.session.query(Message).filter(Message.chat_id == self.chat_id).order_by(Message.created_at.asc())
        )
        return ChatMapper.map_to_chat_response(chat=self.chat_obj, messages=message_objs)
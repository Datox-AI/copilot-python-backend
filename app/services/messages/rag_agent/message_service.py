import uuid
from typing import Annotated
from uuid import UUID
import json
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.enums.message_enums import MessageRole, MessageStatus
from app.infrastructure.RAG_agent.agent_service import RAGAgent
from app.models.maindb import Chat, Message, MessageSharepointDocument
from app.schemas.chat import ChatMapper
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user


class RAGAgentMessageService:
    def __init__(
        self,
        chat_id: UUID,
        user: Annotated[CurrentUser, Depends(current_user)],
        session: Annotated[Session, Depends(create_maindb_session)],
    ) -> None:
        self.session = session
        self.user = user
        # checking chat id
        self._check_chat_id(chat_id=chat_id)
        self.chat_id = chat_id

    def _check_chat_id(self, chat_id):
        self.chat_obj = self.session.query(Chat).filter(Chat.id == chat_id).first()
        if not self.chat_obj:
            raise HTTPException(status_code=404, detail=f"Chat object under {chat_id} id does not exist")
        if self.chat_obj.type != ChatType.FileSearch:
            raise HTTPException(
                status_code=400, detail=f"Chat object under {chat_id} id does not have FileSearch as its chat type"
            )

    def create_user_message(
        self,
        message_text: str,
    ):
        # rag_agent_service
        rag_agent_service = RAGAgent(chat_id=self.chat_id, db_session=self.session)

        def response_generator():
            full_response = ""
            searched_documents = []
            for agent_response, response_type in rag_agent_service.invoke(user_query=message_text):
                if agent_response and response_type == "answer":
                    full_response += agent_response
                    yield f"data: {json.dumps({'Type': 'Text', 'Text': agent_response})}\n\n"

                if agent_response and response_type == "documents":
                    searched_documents = agent_response
                    for document in agent_response:
                        files = []
                        files.append(
                            {
                                "itemName": document.metadata["metadata_spo_item_name"],
                                "contentType": document.metadata["metadata_spo_item_content_type"],
                                "itemUrl": document.metadata["metadata_spo_item_weburi"],
                            }
                        )
                    yield f"""data: {json.dumps({'Type': 'SearchFiles', 'Files': files})}\n\n"""

                # saving messages
            new_user_message = Message(
                id=uuid.uuid4(),
                chat_id=self.chat_id,
                text=message_text,
                status=MessageStatus.Success,
                role=MessageRole.User,
            )
            new_agent_message = Message(
                id=uuid.uuid4(),
                chat_id=self.chat_id,
                text=full_response,
                status=MessageStatus.Success,
                role=MessageRole.Assistant,
            )
            sharepoint_document_objs = []
            for searched_document in searched_documents:
                document_metadata = searched_document.metadata
                sharepoint_document_obj = MessageSharepointDocument(
                    document_id=document_metadata["id"],
                    item_name=document_metadata["metadata_spo_item_name"],
                    item_path=document_metadata["metadata_spo_item_path"],
                    item_url=document_metadata["metadata_spo_item_weburi"],
                    content_type=document_metadata["metadata_spo_item_content_type"],
                    last_modified=document_metadata["metadata_spo_item_last_modified"],
                    item_size=document_metadata["metadata_spo_item_size"],
                    message=new_agent_message,
                )
                sharepoint_document_objs.append(sharepoint_document_obj)
            self.session.add(new_user_message)
            self.session.add(new_agent_message)
            self.session.add_all(sharepoint_document_objs)
            self.session.commit()
            return response_generator()

        return StreamingResponse(
            response_generator(),
            media_type="text/event-stream",
        )

    def get_messages(self):
        message_objs = (
            self.session.query(Message).filter(Message.chat_id == self.chat_id).order_by(Message.created_at.asc())
        )
        return ChatMapper.map_to_RAG_agent_chat_history_response(chat=self.chat_obj, messages=message_objs)

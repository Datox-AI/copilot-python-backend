import json
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.enums.message_enums import MessageRole, MessageStatus
from app.models.maindb import Message, Chat
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.schemas.chat import ChatMapper
from app.shared.auth.azure_scheme import current_user


class AnalyticsAgentMessageCreateService:
    def __init__(
        self,
        user: Annotated[CurrentUser, Depends(current_user)],
        chat_id: UUID,
        session: Annotated[Session, Depends(create_maindb_session)],
    ) -> None:
        self.session = session
        self.user = user
        self.chat_id = chat_id
        print(self.chat_id, " chat_id")

    def create_user_message(
        self,
        message_text: str,
    ):
        new_user_message = Message(
            id=uuid.uuid4(),
            chat_id=self.chat_id,
            text=message_text,
            status=MessageStatus.Success,
            role=MessageRole.User,
        )
        self.session.add(new_user_message)
        self.session.commit()

    def create_agent_response(
        self,
        message_id: UUID,
        agent_response: dict,
    ):
        new_agent_message = Message(
            id=message_id,
            chat_id=self.chat_id,
            text=agent_response["output"],
            status=MessageStatus.Success,
            role=MessageRole.Assistant,
            follow_up_questions=agent_response["followup_questions"],
            stored_file_id=agent_response["stored_file_id"],
            sql_query=agent_response["sql_query"],
            choices=agent_response["choices"],
        )
        self.session.add(new_agent_message)
        self.session.commit()

    def get_messages(self):
        chat_obj = self.session.query(Chat).filter(Chat.id == self.chat_id).first()
        if not chat_obj:
            raise HTTPException(status_code=400, detail=f"Chat object under chat id: {self.chat_id} does not exist")
        message_objs = (
            self.session.query(Message).filter(Message.chat_id == self.chat_id).order_by(Message.created_at.asc())
        )
        return ChatMapper.map_to_data_analytics_chat_history_response(chat=chat_obj, messages=message_objs)

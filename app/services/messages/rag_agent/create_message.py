import json
import uuid
from typing import Annotated, Dict
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.message_enums import MessageRole, MessageStatus
from app.models.maindb import Message
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.shared.auth.azure_scheme import current_user



class RAGAgentMessageCreateService:
    def __init__(
        self,
        user: Annotated[CurrentUser, Depends(current_user)],
        chat_id: UUID,
        session: Annotated[Session, Depends(create_maindb_session)],
    ) -> None:
        self.session = session
        self.user = user
        self.chat_id = chat_id

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
        agent_output: Dict
        
    ):
        print(f"Sources that are not being saved: {agent_output['action_sources']}")
        new_agent_message = Message(
            id=message_id,
            chat_id=self.chat_id,
            text=agent_output["action_input"],
            status=MessageStatus.Success,
            role=MessageRole.Assistant,
        )
        self.session.add(new_agent_message)
        self.session.commit()
        
        return MessageMapper.map_to_RAG_agent_message_response(new_agent_message)


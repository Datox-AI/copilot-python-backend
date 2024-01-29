import uuid, json
from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Annotated

from app.backend.session import create_maindb_session
from app.shared.auth.azure_scheme import current_user
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.models.maindb import Chat, Message
from app.enums.message_enums import MessageRole, MessageStatus
from app.schemas.identity.current_user import CurrentUser
from uuid import UUID



class MessageGetService:
    def __init__(
        self,
        chat_id: UUID,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)]

    ) -> None:
        self.session = session
        self.user = user
        self.chat_id = chat_id
    
    def get_messages(self, chat_id: UUID):
        message_objs = self.session.query(Message).filter(Message.chat_id==chat_id)

        return [MessageMapper.map_to_message_response(message_obj) for message_obj in message_objs]
        

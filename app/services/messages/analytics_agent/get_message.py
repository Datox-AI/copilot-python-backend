import json
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.models.maindb import Chat, Message
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.shared.auth.azure_scheme import current_user


class MessageGetService:
    def __init__(
        self,
        chat_id: UUID,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ) -> None:
        self.session = session
        self.user = user
        self.chat_id = chat_id

    def _check_chat_id(self, chat_id):
        chat_obj = self.session.query(Chat).filter(Chat.id == chat_id).first()
        if not chat_obj:
            raise HTTPException(status_code=404, detail=f"Chat object under {chat_id} id does not exist")
        if chat_obj.type != ChatType.DataAnalytics:
            raise HTTPException(
                status_code=400, detail=f"Chat object under {chat_id} id does not have FileSearch as its chat type"
            )

    def get_messages(self, chat_id: UUID):
        chat_obj = self.session.query(Chat).filter(Chat.id == chat_id).first()
        if not chat_obj:
            raise HTTPException(status_code=400, detail=f"Chat object under chat id: {chat_id} does not exist")
        message_objs = self.session.query(Message).filter(Message.chat_id == chat_id)

        return [MessageMapper.map_to_analytic_agent_message_response(message_obj) for message_obj in message_objs]

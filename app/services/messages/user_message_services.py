import json
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.message_enums import MessageRole, MessageStatus
from app.models.maindb import Chat, Message
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.shared.auth.azure_scheme import current_user


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

    def create_message(
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
        message_response = MessageMapper.map_to_user_message_response(new_user_message)
        message_response_json = json.loads(message_response.model_dump_json())

        return message_response_json

    def get_messages(self, chat_id: UUID):
        chat_obj = self.session.query(Chat).filter(Chat.id == chat_id).first()
        if not chat_obj:
            raise HTTPException(status_code=400, detail=f"Chat object under chat id: {chat_id} does not exist")
        message_objs = self.session.query(Message).filter(Message.chat_id == chat_id)

        return [MessageMapper.map_to_user_message_response(message_obj) for message_obj in message_objs]

    def delete_message(self, chat_id: UUID, message_id: UUID):
        message = self.session.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
        if message:
            self.session.delete(message)
            self.session.commit()
            return True
        return False

    def update_message(self, chat_id: UUID, message_id: UUID, updated_data: dict):
        message = self.session.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
        if message:
            for key, value in updated_data.items():
                setattr(message, key, value)
            self.session.commit()
            return True
        return False

    def delete_messages_batch(self, chat_id: UUID, message_ids: list[UUID]):
        self.session.query(Message).filter(Message.id.in_(message_ids), Message.chat_id == chat_id).delete(
            synchronize_session=False
        )
        self.session.commit()

    def check_chat_exists(self, chat_id: UUID) -> bool:
        return self.session.query(Chat).filter(Chat.id == chat_id).first() is not None

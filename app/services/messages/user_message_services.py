import json
import uuid
from typing import Annotated
from uuid import UUID
from datetime import datetime

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.message_enums import MessageRole, MessageStatus
from app.models.maindb import Chat, Message
from app.schemas.identity.current_user import CurrentUser
from app.schemas.message import MessageMapper
from app.schemas.message.message_request import CreateMessageRequest, DeleteMessagesRequest, UpdateMessageRequest

from app.shared.auth.azure_scheme import current_user

from .message_create_stream import OpenAIChatStream


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
        self.streamer = OpenAIChatStream(model="gpt-35-turbo-16k")

    def create_message(self, request: CreateMessageRequest):
        print(request.id, " message UUID")
        new_user_message = Message(
            id=uuid.uuid4(),
            chat_id=self.chat_id,
            text=request.prompt,
            status=MessageStatus.Success,
            role=MessageRole.User,
        )
        self.session.add(new_user_message)
        response_generator = self.streamer.stream_responses(new_user_message.text)
        self.session.commit()
        return response_generator

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

    def update_message(self, chat_id: UUID, message_id: UUID, updated_data: UpdateMessageRequest):
        message_obj = self.session.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
        if message_obj:
            if message_obj.id != updated_data.id:
                raise HTTPException(status_code=400, detail="Message ID you provided is wrong")
            message_obj.pinned = updated_data.pinned
            if message_obj.pinned:
                message_obj.pinned_date = datetime.now()
            self.session.commit()

            return message_obj
        else:
            raise HTTPException(status_code=404, detail="Message not found")

    def delete_messages_batch(self, chat_id: UUID, request: DeleteMessagesRequest):
        message_ids = [request.ids]
        self.session.query(Message).filter(Message.id.in_(message_ids), Message.chat_id == chat_id).delete(
            synchronize_session=False
        )
        self.session.commit()

    def check_chat_exists(self, chat_id: UUID) -> bool:
        return self.session.query(Chat).filter(Chat.id == chat_id).first() is not None

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


class MessageService:
    def __init__(
        self,
        user: CurrentUser,
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
        new_message = Message(
            id=uuid.uuid4(),
            chat_id=self.chat_id,
            text=message_text,
            status=MessageStatus.Success,
            role=MessageRole.User,
        )
        self.session.add(new_message)
        self.session.commit()
        message_response = MessageMapper.map_to_message_response(new_message)
        message_response_json = json.loads(message_response.model_dump_json())

        return message_response_json

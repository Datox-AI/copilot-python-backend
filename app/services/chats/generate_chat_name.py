from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.models.maindb import Chat, Message
from app.schemas.message import MessageMapper

from app.services.messages.message_create_stream import OpenAIChatStream


class GenerateChatName:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)]) -> None:
        self.session = session
        self.generator = OpenAIChatStream()

    def invoke(self, id: UUID) -> str:
        entity = self.session.execute(select(Chat).where(Chat.id == id, Chat.is_deleted == False))
        entity = entity.scalars().first()

        if not entity:
            raise HTTPException(status_code=404, detail="Chat not found")

        message_objs = (
            self.session.query(Message)
            .filter(Message.chat_id == id)
            .order_by(Message.created_at.desc())  # Сортируем по убыванию, чтобы получить последние сообщения
            .limit(3)  # Ограничиваем выборку тремя последними сообщениями
            .all()  # Получаем все объекты, удовлетворяющие условиям
        )

        message_list = [MessageMapper.map_to_user_message_response(message_obj) for message_obj in message_objs]

        generated_name = self.generator.name_generate(message_list)

        return generated_name

from typing import Annotated, List
from fastapi import Depends
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Session, aliased
from app.backend.session import create_maindb_session

from app.models.maindb import Chat, Message, MessageFile
from app.schemas.chat import ChatResponse, ChatMapper


class GetChat:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)]) -> None:
        self.session = session

    async def invoke(self, user_id: UUID) -> List[ChatResponse]:
        MessageFileAlias = aliased(MessageFile)
        subquery = (
            select(
                Message.chat_id,
                func.count(Message.id).label("messages_count"),
                func.count(MessageFileAlias.id).label("files_count"),
                func.max(Message.created).label("last_message")
            )
            .outerjoin(MessageFileAlias, Message.message_files)
            .group_by(Message.chat_id)
            .subquery()
        )

        result = await self.session.execute(
            select(Chat, subquery.c.messages_count, subquery.c.files_count, subquery.c.last_message)
            .outerjoin(subquery, Chat.id == subquery.c.chat_id)
            .where(Chat.created_by == user_id, Chat.is_deleted == False)
            .order_by(desc(Chat.pinned), 
                      Chat.pinned_date if Chat.pinned else func.max(),
                      desc(Chat.created))
        )

        return [
            ChatMapper.map_to_chat_response(chat, messages_count, files_count, last_message)
            for chat, messages_count, files_count, last_message in result.all()
        ]

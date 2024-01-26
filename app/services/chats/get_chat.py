from typing import Annotated, List, Optional

from fastapi import Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, aliased

from app.backend.session import create_maindb_session
from app.models.admindb.application_user import ApplicationUser
from app.models.maindb import Chat, Message, MessageFile
from app.schemas.chat import ChatHistoryResponse, ChatMapper, ChatResponse
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user
from app.enums.chat_enums import ChatType

class GetChat:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ) -> None:
        self.session = session
        self.user = user

    def get_chat_list(self, chat_type: str = None, user_id: UUID | None = None) -> list[ChatResponse]:
        # checking chat type
        # if chat_type =
        if not user_id:
            user_id = self.user.user_id
        elif user_id != self.user.user_id:
            result = self.session.execute(select(ApplicationUser).where(ApplicationUser.id == user_id))
            user = result.scalars().first()

            if user is None:
                raise HTTPException(status_code=404, detail="User not found")

            if "Admin" not in self.user.roles or self.user.tenant_id != user.tenant_id:
                raise HTTPException(status_code=403, detail="Forbidden access")

        MessageFileAlias = aliased(MessageFile)
        subquery = (
            select(
                Message.chat_id,
                func.coalesce(func.count(Message.id), 0).label("messages_count"),
                func.coalesce(func.count(MessageFileAlias.id), 0).label("files_count"),
                func.max(Message.created_at).label("last_message"),
            )
            .outerjoin(MessageFileAlias, Message.message_files)
            .group_by(Message.chat_id)
            .subquery()
        )
        # Base query
        query = (
            select(
                Chat,
                func.coalesce(subquery.c.messages_count, 0),
                func.coalesce(subquery.c.files_count, 0),
                subquery.c.last_message,
            )
            .outerjoin(subquery, Chat.id == subquery.c.chat_id)
            .where(Chat.created_by == user_id, Chat.is_deleted == False)
            .order_by(desc(Chat.pinned), Chat.pinned_date if Chat.pinned else func.max(), desc(Chat.created_at))
        )
        # Filter by chat_type if provided
        if chat_type is not None and chat_type in (item.value for item in ChatType.__members__.values()):
            query = query.where(Chat.type == chat_type)

        result = self.session.execute(query).unique()

        return [
            ChatMapper.map_to_chat_response(chat, messages_count, files_count, last_message)
            for chat, messages_count, files_count, last_message in result
        ]

    def get_chat_history(self, chat_id: UUID) -> ChatHistoryResponse:
        chat_obj = self.session.query(Chat).filter(Chat.id == chat_id).first()

        return ChatMapper.map_to_chat_history_response(chat=chat_obj)

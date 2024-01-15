from typing import Annotated, List, Optional
from fastapi import Depends, HTTPException
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, aliased
from app.backend.session import create_maindb_session
from app.models.admindb.application_user import ApplicationUser

from app.models.maindb import Chat, Message, MessageFile
from app.schemas.chat import ChatResponse, ChatMapper
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user

class GetChat:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)],
                 user: Annotated[CurrentUser, Depends(current_user)]) -> None:
        self.session = session
        self.user = user

    def invoke(self, user_id: Optional[UUID] = None) -> List[ChatResponse]:
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
                func.max(Message.created_at).label("last_message")
            )
            .outerjoin(MessageFileAlias, Message.message_files)
            .group_by(Message.chat_id)
            .subquery()
        )

        result = self.session.execute(
            select(Chat, func.coalesce(subquery.c.messages_count, 0), func.coalesce(subquery.c.files_count, 0), subquery.c.last_message)
            .outerjoin(subquery, Chat.id == subquery.c.chat_id)
            .where(Chat.created_by == user_id, Chat.is_deleted == False)
            .order_by(desc(Chat.pinned), 
                      Chat.pinned_date if Chat.pinned else func.max(),
                      desc(Chat.created_at))
        ).unique()

        return [
            ChatMapper.map_to_chat_response(chat, messages_count, files_count, last_message)
            for chat, messages_count, files_count, last_message in result
        ]

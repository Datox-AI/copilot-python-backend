from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.models.maindb import Chat
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user


class DeleteChat:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ) -> None:
        self.session = session
        self.user = user

    def invoke(self, chat_id: UUID) -> None:
        # Asynchronously fetch the chat
        result = self.session.execute(select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False))
        chat = result.scalars().first()

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID {chat_id} not found.",
            )

        # Mark the chat as deleted
        chat.is_deleted = True
        chat.deleted_at = datetime.now()
        chat.deleted_by = self.user.user_id

        self.session.add(chat)
        self.session.commit()

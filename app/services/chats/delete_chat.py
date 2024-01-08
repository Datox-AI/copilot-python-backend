import datetime
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import UUID, select
from sqlalchemy.orm import Session
from app.backend.session import create_maindb_session

from app.models.maindb import Chat

class DeleteChat:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)]) -> None:
        self.session = session

    async def invoke(self, chat_id: UUID) -> None:
        # Asynchronously fetch the chat
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)
        )
        chat = result.scalars().first()

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID {chat_id} not found."
            )

        # Mark the chat as deleted
        chat.is_deleted = True
        chat.deleted_at = datetime.utcnow()

        self.session.add(chat)
        await self.session.commit()
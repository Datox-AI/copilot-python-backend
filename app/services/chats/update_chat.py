from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.backend.session import create_maindb_session

from app.models.maindb import Chat
from app.schemas.chat import UpdateChatRequest

class UpdateChat:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)]) -> None:
        self.session = session

    def invoke(self, model: UpdateChatRequest) -> None:
        entity = self.session.execute(
            select(Chat).where(Chat.id == model.id, Chat.is_deleted == False)
        )
        entity = entity.scalars().first()

        if not entity:
            raise HTTPException(status_code=404, detail="Chat not found")

        entity.name = model.name if model.name is not None else entity.name
        entity.pinned = model.pinned

        self.session.commit()
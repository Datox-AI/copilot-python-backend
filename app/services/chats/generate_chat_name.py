from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import UUID, select
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.models.maindb import Chat


class GenerateChatName:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)]) -> None:
        self.session = session

    def invoke(self, id: UUID) -> str:
        entity = self.session.execute(select(Chat).where(Chat.id == id, Chat.is_deleted == False))
        entity = entity.scalars().first()

        if not entity:
            raise HTTPException(status_code=404, detail="Chat not found")

        # TODO: Implement name generation logic here

        return "Test Name"

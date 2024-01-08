import uuid
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.backend.session import create_maindb_session

from app.models.maindb import Chat
from app.schemas.chat import CreateChatRequest, ChatResponse, ChatMapper

class CreateChat:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)]) -> None:
        self.session = session
        
    def invoke(self, model: CreateChatRequest) -> ChatResponse:
        new_chat = Chat(
            id=uuid.uuid4(),
            name="New Chat",
            type=model.type 
        )

        self.session.add(new_chat)
        self.session.commit()
        
        return ChatMapper.map_to_chat_response(new_chat, 0, 0)

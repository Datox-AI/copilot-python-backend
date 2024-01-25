import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.models.maindb import Chat, ChatSnowflakeData
from app.schemas.chat import CreateChatRequest, ChatResponse, ChatMapper
from app.backend.session import create_maindb_session
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user


class CreateChat:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ) -> None:
        self.session = session
        self.user = user

    def invoke(self, model: CreateChatRequest) -> ChatResponse:
        new_chat = Chat(
            id=uuid.uuid4(),
            name="New Chat",
            type=model.type
        )
        if model.snowflake_data:
            snowflake_data = ChatSnowflakeData(
                id=uuid.uuid4(),
                snowflake_account=model.snowflake_data.snowflake_account,
                database_name=model.snowflake_data.database_name,
                schema=model.snowflake_data.snowflake_schema,
                warehouse=model.snowflake_data.warehouse
            )
            new_chat.snowflake_data = snowflake_data
            
        self.session.add(new_chat)
        self.session.commit()

        return ChatMapper.map_to_chat_response(new_chat, 0, 0)
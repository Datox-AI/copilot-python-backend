from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.models.maindb import Chat
from app.schemas.chat import UpdateChatRequest, UpdateChatSnowflakeDataRequest


class UpdateChat:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)]) -> None:
        self.session = session

    def invoke(self, model: UpdateChatRequest) -> None:
        entity = self.session.execute(select(Chat).where(Chat.id == model.id, Chat.is_deleted == False))
        entity = entity.scalars().first()

        if not entity:
            raise HTTPException(status_code=404, detail="Chat not found")

        entity.name = model.name if model.name is not None else entity.name
        entity.pinned = model.pinned if model.pinned is not None else entity.pinned

        self.session.commit()

class UpdateChatSnowflakeData:
    def __init__(self, session: Annotated[Session, Depends(create_maindb_session)]) -> None:
        self.session = session

    def invoke(self, model: UpdateChatSnowflakeDataRequest) -> None:
        entity = self.session.execute(select(Chat).where(Chat.id == model.chat_id, Chat.is_deleted == False))
        entity = entity.scalars().first()

        if not entity:
            raise HTTPException(status_code=404, detail="Chat not found")
        if entity.type != ChatType.DataAnalytics:
            raise HTTPException(status_code=404, detail="Chat type must be DataAnalytics to update snowflake data")
        snowflake_data_obj = entity.snowflake_data
        snowflake_data_obj.snowflake_account = model.snowflake_account if model.snowflake_account is not None else snowflake_data_obj.snowflake_account
        snowflake_data_obj.database_name = model.database_name if model.database_name is not None else snowflake_data_obj.database_name
        snowflake_data_obj.schema = model.snowflake_schema if model.snowflake_schema is not None else snowflake_data_obj.schema
        snowflake_data_obj.warehouse = model.warehouse if model.warehouse is not None else snowflake_data_obj.warehouse

        self.session.commit()

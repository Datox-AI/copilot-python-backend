from uuid import UUID

from pydantic import ValidationError, model_validator, root_validator

from app.enums import ChatType
from app.schemas.base import BaseSchema


class CreateChatSnowlfakeData(BaseSchema):
    snowflake_account: str
    database_name: str
    snowflake_schema: str
    warehouse: str


class CreateChatRequest(BaseSchema):
    type: ChatType
    snowflake_data: CreateChatSnowlfakeData | None = None
    assistant_id: str | None = None

    @model_validator(mode="after")
    def check_snowflake_data(self):
        chat_type = self.type
        snowflake_data = self.snowflake_data
        if chat_type == ChatType.DataAnalytics and not snowflake_data:
            raise ValueError("snowflake_data is required for DataAnalytics chat type")
        return self
    
    
    @model_validator(mode="after")
    def check_assistant_id(self):
        chat_type = self.type
        assistant_id = self.assistant_id
        if chat_type == ChatType.Assistant and not assistant_id:
            raise ValueError("assistant_id is required for Assistants chat type")
        return self


class UpdateChatRequest(BaseSchema):
    id: UUID
    name: str | None
    pinned: bool | None


class UpdateChatSnowflakeDataRequest(BaseSchema):
    chat_id: UUID
    snowflake_account: str | None
    database_name: str | None
    snowflake_schema: str | None
    warehouse: str | None

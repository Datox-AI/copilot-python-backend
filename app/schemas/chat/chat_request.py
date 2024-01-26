from uuid import UUID
from pydantic import root_validator, model_validator, ValidationError

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

    @model_validator(mode='after')
    def check_snowflake_data(self):
        chat_type = self.type
        snowflake_data = self.snowflake_data
        if chat_type== ChatType.DataAnalytics and not snowflake_data:
            raise ValueError('snowflake_data is required for DataAnalytics chat type')
        return self
    

class UpdateChatRequest(BaseSchema):
    id: UUID
    name: str
    pinned: bool

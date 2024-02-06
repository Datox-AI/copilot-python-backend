from datetime import datetime
from typing import Optional

from app.models.maindb import Chat
from app.schemas.chat import ChatHistoryResponse, ChatResponse, ChatSnowflakeData
from app.schemas.message import AnalyticAgentMessageResponse


class ChatMapper:
    @staticmethod
    def map_to_chat_response(
        chat: Chat,
        messages_count: int,
        files_count: int,
        last_message: datetime | None = None,
    ) -> ChatResponse:
        if chat.snowflake_data:
            snowflake_data_response = ChatSnowflakeData(
                id=chat.snowflake_data.id,
                snowflake_account=chat.snowflake_data.snowflake_account,
                database_name=chat.snowflake_data.database_name,
                snowflake_schema=chat.snowflake_data.schema,
                warehouse=chat.snowflake_data.warehouse,
            )
        else:
            snowflake_data_response = None
        return ChatResponse(
            id=chat.id,
            name=chat.name,
            created=chat.created_at,
            pinned=chat.pinned,
            pinned_date=chat.pinned_date,
            type=chat.type,
            messages_count=messages_count,
            files_count=files_count,
            last_message=last_message,
            snowflake_data=snowflake_data_response,
        )

    @staticmethod
    def map_to_chat_history_response(chat: Chat):
        message_responses = [
            AnalyticAgentMessageResponse(
                id=message.id,
                chat_id=message.chat_id,
                text=message.text,
                role=message.role,
            )
            for message in chat.messages
        ]
        snowflake_data_response = ChatSnowflakeData(
            id=chat.snowflake_data.id,
            snowflake_account=chat.snowflake_data.snowflake_account,
            database_name=chat.snowflake_data.database_name,
            snowflake_schema=chat.snowflake_data.schema,
            warehouse=chat.snowflake_data.warehouse,
        )

        return ChatHistoryResponse(
            id=chat.id,
            name=chat.name,
            created=chat.created_at,
            type=chat.type,
            snowflake_data=snowflake_data_response,
            messages=message_responses,
        )

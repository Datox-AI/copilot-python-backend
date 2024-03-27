from datetime import datetime
from typing import List

from app.models.maindb import Chat, Message
from app.schemas.chat import ChatHistoryResponse, ChatResponse, ChatSnowflakeData
from app.schemas.message import MessageMapper


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
            assistant_thread_id=chat.assistant_thread_id,
            assistant_id=chat.assistant_id,
            last_message=last_message,
            snowflake_data=snowflake_data_response,
        )

    @staticmethod
    def map_to_data_analytics_chat_history_response(chat: Chat, messages: List[Message]):
        message_responses = [
            MessageMapper.map_to_analytic_agent_message_response(message=message_obj) for message_obj in messages
        ]

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
            
        return ChatHistoryResponse(
            id=chat.id,
            name=chat.name,
            created=chat.created_at,
            type=chat.type,
            snowflake_data=snowflake_data_response,
            messages=message_responses,
        )

    @staticmethod
    def map_to_RAG_agent_chat_history_response(chat: Chat, messages: List[Message]):
        message_responses = [
            MessageMapper.map_to_RAG_agent_message_response(message=message_obj) for message_obj in messages
        ]

        return ChatHistoryResponse(
            id=chat.id,
            name=chat.name,
            created=chat.created_at,
            type=chat.type,
            messages=message_responses,
        )

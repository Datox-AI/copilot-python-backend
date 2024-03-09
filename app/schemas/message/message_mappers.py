import json

from app.models.maindb import Message
from app.schemas.message.message_response import (
    AnalyticAgentMessageResponse,
    RAGAgentMessageResponse,
    SharePointFilesResponse,
    UserMessageResponse,
)


class MessageMapper:
    @staticmethod
    def map_to_analytic_agent_message_response(message: Message):
        # if message.choices is not None or message.choices != []:
            # followup_questions = message.choices
        # else:
        followup_questions = message.follow_up_questions
        return AnalyticAgentMessageResponse(
            id=message.id.hex,
            chat_id=message.chat_id,
            text=message.text,
            role=message.role,
            created_at=message.created_at,
            follow_up_questions=followup_questions,
            sql_query=message.sql_query,
            stored_file_id=message.stored_file_id,
        )

    @staticmethod
    def map_to_RAG_agent_message_response(message: Message):
        searched_files_responses = [
            SharePointFilesResponse(
                id=sharepoint_file.id,
                item_name=sharepoint_file.item_name,
                item_url=sharepoint_file.item_url,
                item_size=sharepoint_file.item_size,
                content_type=sharepoint_file.content_type,
                last_modified=sharepoint_file.last_modified,
            )
            for sharepoint_file in message.message_sharepoint_documents
        ]
        return RAGAgentMessageResponse(
            id=message.id.hex,
            chat_id=message.chat_id,
            text=message.text,
            role=message.role,
            created_at=message.created_at,
            searched_files=searched_files_responses,
        )

    @staticmethod
    def map_to_user_message_response(message: Message):
        return UserMessageResponse(
            id=message.id.hex,
            chat_id=message.chat_id,
            text=message.text,
            role=message.role,
            pinned=message.pinned,
            pinned_date=message.pinned_date,
            status=message.status,
            reply_to=message.reply_to_id,
            questions=message.follow_up_questions,
            created_at=message.created_at,
            prompt_id=message.prompt_id,
        )

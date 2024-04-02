from app.models.maindb import Message
from app.schemas.message.message_response import (
    AnalyticAgentMessageResponse,
    AssistantMessageDocument,
    RAGAgentMessageResponse,
    SharePointFilesResponse,
    UserMessageResponse,
)


class MessageMapper:
    @staticmethod
    def map_to_analytic_agent_message_response(message: Message):
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
        files_info = []
        if message.message_files:
            files_info = [
                {
                    "file_id": file.file_id,
                    "fileName": file.file.file_name,
                    "fileType": file.file.file_extension,
                    "blob_name": file.file.blob_name,
                }
                for file in message.message_files
            ]
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
            files=files_info,
            searched_files=[],
        )

    @staticmethod
    def map_to_assistant_message_response(message: Message):
        assistant_message_documents = []
        print(message)
        if message.message_assistant_documents:
            for asst_msg_doc in message.message_assistant_documents:
                # Check if the document with the same blob name already exists
                existing_doc = next(
                    (
                        doc
                        for doc in assistant_message_documents
                        if doc.blob_name == asst_msg_doc.assistant_file.blob_name
                    ),
                    None,
                )
                if existing_doc:
                    # If the document already exists, skip adding it again
                    continue
                assistant_message_documents.append(
                    AssistantMessageDocument(
                        name=asst_msg_doc.assistant_file.name,
                        type=asst_msg_doc.assistant_file.type,
                        blob_name=asst_msg_doc.assistant_file.blob_name,
                    )
                )
        if message.message_files:
            files_info = [
                {
                    "file_id": file.file_id,
                    "fileName": file.file.file_name,
                    "fileType": file.file.file_extension,
                    "blob_name": file.file.blob_name,
                }
                for file in message.message_files
            ]
        else:
            files_info = []
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
            searched_files=assistant_message_documents,
            files=files_info,
        )

from app.models.maindb import Message
from app.schemas.message.message_response import MessageResponse, UserMessageResponse


class MessageMapper:
    @staticmethod
    def map_to_message_response(message: Message):
        return MessageResponse(
            id=message.id.hex,
            chat_id=message.chat_id,
            text=message.text,
            role=message.role,
            created_at=message.created_at,
            follow_up_questions=message.follow_up_questions,
            sql_query=message.sql_query,
            stored_file_id=message.stored_file_id,
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
            questions=message.reply_to_message,
            created_at=message.created_at,
        )

from app.models.maindb import Message
from app.schemas.message import MessageResponse


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

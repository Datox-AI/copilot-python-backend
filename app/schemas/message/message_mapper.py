from app.models.maindb import Message
from app.schemas.message import MessageResponse
from app.schemas.message import MessageResponse


class MessageMapper:
    @staticmethod
    def map_to_message_response(message: Message):
        return MessageResponse(
            id=message.id.hex,
            chat_id=message.chat_id,
            text=message.text,
            role=message.role,
        )

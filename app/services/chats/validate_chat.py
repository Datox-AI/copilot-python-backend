from app.models.maindb import Chat


def validate_chat(session, chat_id, chat_type):
    is_valid = False
    error_message = None
    chat = session.query(Chat).filter(Chat.id == chat_id).first()

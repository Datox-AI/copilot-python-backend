from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship, remote, foreign, backref
from sqlalchemy.dialects.postgresql import UUID

from ..base_models import BaseDelete
from app.enums.message_enums import MessageRole, MessageStatus

class Message(BaseDelete):
    __table_args__ = ({ 'info': { 'dbname': 'main' }})
    __tablename__ = 'messages'

    chat_id = Column(UUID(as_uuid=True), ForeignKey('chats.id'), nullable=False)
    text = Column(String, nullable=False)
    error_message = Column(String, nullable=True)
    pinned = Column(Boolean, default=False)
    pinned_date = Column(DateTime, nullable=True)
    status = Column(Enum(MessageStatus))
    role = Column(Enum(MessageRole))
    follow_up_questions = Column(String, nullable=True)
    search_query = Column(String, nullable=True)
    reply_to_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=True)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=True)

    chat = relationship("Chat", back_populates="messages")
    reply_to_message = relationship(
        'Message',
        backref="replies",
        remote_side=[BaseDelete.id],
        primaryjoin="Message.reply_to_id==remote(foreign(Message.id))",
    )
    
    prompt_message = relationship(
        'Message',
        backref="prompts",
        remote_side=[BaseDelete.id],
        primaryjoin="Message.prompt_id==remote(foreign(Message.id))",
        overlaps="replies,reply_to_message"
    )
    # prompt = relationship(
    #     'Message',
    #     # remote_side = [text],
    #     uselist=False
    # )
    # reply_to_message = relationship('Message', remote_side=[BaseDelete.id], foreign_keys=[reply_to_id], uselist=False)
    # prompt = relationship("Message", remote_side=[BaseDelete.id], foreign_keys=[prompt_id], uselist=False)
    message_files = relationship("MessageFile", back_populates="message")
    message_sharepoint_documents = relationship("MessageSharepointDocument", back_populates="message")
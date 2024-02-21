from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import backref, foreign, relationship, remote

from app.enums.message_enums import MessageRole, MessageStatus

from ..base_models import BaseDelete


class Message(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "messages"

    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    text = Column(String, nullable=False)
    error_message = Column(String, nullable=True)
    pinned = Column(Boolean, default=False)
    pinned_date = Column(DateTime, nullable=True)
    status = Column(Enum(MessageStatus))
    role = Column(Enum(MessageRole))
    search_query = Column(String, nullable=True)
    sql_query = Column(String, nullable=True)
    stored_file_id = Column(String, nullable=True)
    follow_up_questions = Column(JSONB, nullable=True)
    choices = Column(JSONB, nullable=True)

    reply_to_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)

    chat = relationship("Chat", back_populates="messages")
    reply_to_message = relationship(
        "Message",
        backref=backref("replies", overlaps="prompts,prompt_message"),
        remote_side=[BaseDelete.id],
        primaryjoin="Message.reply_to_id==remote(foreign(Message.id))",
        overlaps="prompts,prompt_message",
    )

    prompt_message = relationship(
        "Message",
        backref=backref("prompts", overlaps="replies,reply_to_message"),
        remote_side=[BaseDelete.id],
        primaryjoin="Message.prompt_id==remote(foreign(Message.id))",
        overlaps="replies,reply_to_message",
    )

    message_files = relationship("MessageFile", back_populates="message")
    message_sharepoint_documents = relationship("MessageSharepointDocument", back_populates="message")

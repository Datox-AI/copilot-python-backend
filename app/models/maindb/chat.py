from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from ..base_models import BaseDelete

from app.enums.chat_enums import ChatType, ChatModel


class Chat(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "chats"

    name = Column(String, nullable=False)
    type = Column(Enum(ChatType))
    pinned = Column(Boolean, default=False)
    pinned_date = Column(DateTime, nullable=True)
    chat_model = Column(Enum(ChatModel), default=ChatModel.GPT3_16K)

    messages = relationship("Message", back_populates="chat", lazy="joined")

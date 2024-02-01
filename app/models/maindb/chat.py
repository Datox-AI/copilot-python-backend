from sqlalchemy import Column, String, Enum, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
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
    snowflake_data_id = Column(UUID(as_uuid=True), ForeignKey('chat_snowflake_data.id'), nullable=True)

    snowflake_data = relationship("ChatSnowflakeData", back_populates="chat", uselist=False)
    messages = relationship("Message", back_populates="chat", lazy="joined")



class ChatSnowflakeData(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "chat_snowflake_data"
    
    snowflake_account = Column(String)
    database_name = Column(String)
    schema = Column(String)
    warehouse = Column(String)

    chat = relationship("Chat", back_populates="snowflake_data", uselist=False)




    
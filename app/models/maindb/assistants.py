from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base_models import BaseDelete


class Assistant(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "assistants"
    
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    instructions = Column(String, nullable=False)
    assistant_id = Column(String, nullable=False)
    
    knowledge_files = relationship("AssistantFile", back_populates="assistant")
    chats = relationship("Chat", back_populates="assistant")
    
    
class AssistantFile(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "assistantFiles"
    
    name = Column(String)
    type = Column(String)
    # is_deleted = Column(Boolean, default=False)
    assistant_id = Column(UUID(as_uuid=True), ForeignKey("assistants.id"))
    assistant = relationship("Assistant", back_populates="knowledge_files")

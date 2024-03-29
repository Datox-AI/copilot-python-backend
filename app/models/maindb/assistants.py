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
    icon_file_name = Column(String, nullable=True)
    
    knowledge_files = relationship("AssistantFile", back_populates="assistant")
    chats = relationship("Chat", back_populates="assistant")
    
    
class AssistantFile(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "assistantFiles"
    
    name = Column(String)
    type = Column(String)
    blob_name = Column(String, nullable=True)
    assistant_id = Column(UUID(as_uuid=True), ForeignKey("assistants.id"))
    
    assistant = relationship("Assistant", back_populates="knowledge_files")
    message_assistant_documents = relationship("MessageAssistantDocument", back_populates="assistant_file")



class MessageAssistantDocument(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "message_assistant_documents"

    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    document_id = Column(String, nullable=False)
    assistant_file_id = Column(UUID(as_uuid=True), ForeignKey("assistantFiles.id"), nullable=False)

    message = relationship("Message", back_populates="message_assistant_documents")
    assistant_file = relationship("AssistantFile", back_populates="message_assistant_documents")
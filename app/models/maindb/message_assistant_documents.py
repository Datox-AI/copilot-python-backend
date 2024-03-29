from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..base_models import BaseAudit


class MessageAssistantDocument(BaseAudit):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "message_assistant_documents"

    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    document_id = Column(String, nullable=False)
    assistant_file_id = Column(UUID(as_uuid=True), ForeignKey("assistantFiles.id"), nullable=False)

    message = relationship("Message", back_populates="message_assistant_documents")
    assistant_file = relationship("AssistantFile", back_populates="message_assistant_documents")
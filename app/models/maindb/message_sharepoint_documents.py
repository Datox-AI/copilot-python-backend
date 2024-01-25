from sqlalchemy import Column, ForeignKey, String, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..base_models import BaseAudit


class MessageSharepointDocument(BaseAudit):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "message_sharepoint_documents"

    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    document_id = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    item_path = Column(String, nullable=False)
    item_url = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    last_modified = Column(DateTime, nullable=False)
    item_size = Column(BigInteger, nullable=False)

    message = relationship("Message", back_populates="message_sharepoint_documents")

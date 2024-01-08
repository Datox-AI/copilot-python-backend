from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from ..base_models import BaseAudit

class MessageFile(BaseAudit):
    __table_args__ = ({ 'info': { 'dbname': 'main' }})
    __tablename__ = 'message_files'

    message_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey('files.id'), nullable=False)
    content = Column(String, nullable=True)
    token = Column(Integer, nullable=True)
    
    
    message = relationship("Message", back_populates="message_files")
    file = relationship("File")
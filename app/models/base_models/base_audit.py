from sqlalchemy import Column, event, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.shared.context import current_user_id

from .base import Base

class BaseAudit(Base):
    """
    Base Audit Model Class for Common Audit Attributes.
    """
    
    __abstract__ = True
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(UUID(as_uuid=True), nullable=True)

@event.listens_for(BaseAudit, "before_insert", propagate=True)    
def before_insert(mapper, connection, target):
    if isinstance(target, BaseAudit):
        user_id = current_user_id.get()
        target.created_by = user_id

@event.listens_for(BaseAudit, "before_update", propagate=True)
def before_update(mapper, connection, target):
    if isinstance(target, BaseAudit):
        user_id = current_user_id.get()
        target.modified_by = user_id 

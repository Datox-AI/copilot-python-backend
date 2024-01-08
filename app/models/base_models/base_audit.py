import datetime
from sqlalchemy import Column, event, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

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

    
def before_insert(mapper, connection, target):
    if isinstance(target, BaseAudit):
        now = datetime.utcnow()
        user_id = None
        target.created = now
        target.created_by = user_id

def before_update(mapper, connection, target):
    if isinstance(target, BaseAudit):
        now = datetime.utcnow()
        user_id = None
        target.last_modified = now
        target.last_modified_by = user_id

def setup_audit_listeners():
    event.listen(BaseAudit, 'before_insert', before_insert)
    event.listen(BaseAudit, 'before_update', before_update)
    

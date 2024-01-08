from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, DateTime, Boolean

from .base_audit import BaseAudit


class BaseDelete(BaseAudit):
    """
    Base Delete Model Class for Soft Deletion.
    """
    
    __abstract__ = True
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
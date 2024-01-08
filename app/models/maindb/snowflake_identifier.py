from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from ..base_models import BaseAudit

class SnowflakeIdentifier(BaseAudit):
    __table_args__ = ({ 'info': { 'dbname': 'main' }})
    __tablename__ = 'snowflake_identifiers'

    user_id = Column(UUID(as_uuid=True), nullable=False)
    identifier = Column(String, nullable=False)
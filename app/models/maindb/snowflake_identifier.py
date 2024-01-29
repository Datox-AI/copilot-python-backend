from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from ..base_models import BaseAudit


class SnowflakeIdentifier(BaseAudit):
    __table_args__ = ({'info': {'dbname': 'main'}})
    __tablename__ = 'snowflake_identifiers'

    user_id = Column(UUID(as_uuid=True), unique=True)
    account_identifier = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    token_endpoint = Column(String, nullable=False)
    authorization_endpoint = Column(String, nullable=False)
    warehouse = Column(String, nullable=True)
 


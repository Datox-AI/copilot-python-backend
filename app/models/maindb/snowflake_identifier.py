from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from ..base_models import BaseAudit


class SnowflakeIdentifier(BaseAudit):
    __table_args__ = ({'info': {'dbname': 'main'}})
    __tablename__ = 'snowflake_identifiers'

    # user_id = Column(UUID(as_uuid=True), nullable=False)
    account_identifier = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    token_endpoint = Column(String, nullable=False)
 


# class a
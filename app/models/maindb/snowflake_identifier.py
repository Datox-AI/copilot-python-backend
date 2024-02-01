from sqlalchemy import Column, String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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

    warehouses = relationship('SnowflakeWarehouse',  back_populates="identifier")


class SnowflakeWarehouse(BaseAudit):
    __table_args__ = ({'info': {'dbname': 'main'}})
    __tablename__ = 'snowflake_warehouses'

    name = Column(String)
    identifier_id = Column(UUID(as_uuid=True), ForeignKey("snowflake_identifiers.id"))
    selected = Column(Boolean, default=False)       
    
    identifier = relationship(SnowflakeIdentifier, back_populates="warehouses")


from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from ..base_models import Base


class Tenant(Base):
    __table_args__ = ({'info': {'dbname': 'admin'}})
    __tablename__ = 'tenants'
    
    azure_object_id = Column(String, nullable=False)
    tenant_name = Column(String, nullable=False)

    users = relationship('ApplicationUser', back_populates="tenant")
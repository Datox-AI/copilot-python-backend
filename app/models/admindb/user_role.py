from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..base_models import Base


class UserRole(Base):
    __table_args__ = {"info": {"dbname": "admin"}}
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("application_users.id"))
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"))

    user = relationship("ApplicationUser", back_populates="user_roles")
    role = relationship("Role")

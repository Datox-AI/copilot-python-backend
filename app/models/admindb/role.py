from sqlalchemy import Column, String

from ..base_models import Base


class Role(Base):
    __table_args__ = {"info": {"dbname": "admin"}}
    __tablename__ = "roles"

    name = Column(String, nullable=False)

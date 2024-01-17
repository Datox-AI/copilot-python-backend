from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column
from sqlalchemy.sql import func
import uuid
from sqlalchemy.ext.declarative import declarative_base

DeclarativeBase = declarative_base()


class Base(DeclarativeBase):
    """
    Base Model Class for Common Attributes.
    """

    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

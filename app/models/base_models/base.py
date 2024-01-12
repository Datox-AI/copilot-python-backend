from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column
from sqlalchemy.sql import func
import uuid
<<<<<<< HEAD
from sqlalchemy.ext.declarative import declarative_base

# from sqlalchemy.orm.decl_api import DeclarativeBase

DeclarativeBase = declarative_base()

=======
# from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.declarative import declarative_base

DeclarativeBase = declarative_base()
>>>>>>> e26444a36e58f222100773c7b73ba5dd51956bbf

class Base(DeclarativeBase):
    """
    Base Model Class for Common Attributes.
    """
    
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
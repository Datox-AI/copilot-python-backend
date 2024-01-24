from sqlalchemy import Column, String
from ..base_models import BaseDelete


class File(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "files"

    fileName = Column(String, nullable=False)
    blobName = Column(String, nullable=False)

from sqlalchemy import Column, String

from ..base_models import BaseDelete


class File(BaseDelete):
    __table_args__ = {"info": {"dbname": "main"}}
    __tablename__ = "files"

    file_name = Column(String, nullable=False)
    blob_name = Column(String, nullable=False)
    file_extension = Column(String, nullable=False)

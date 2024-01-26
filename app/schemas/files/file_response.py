from app.schemas.base import BaseSchema
from datetime import datetime
from typing import List
from uuid import UUID


class FilesDetailResponse(BaseSchema):
    id: UUID
    filename: str
    created: datetime
    fileExtension: str


class FileResponseByChatID(BaseSchema):
    lists: List[FilesDetailResponse]

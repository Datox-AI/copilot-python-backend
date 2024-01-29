from datetime import datetime
from typing import List
from uuid import UUID

from app.schemas.base import BaseSchema


class FilesDetailResponse(BaseSchema):
    id: UUID
    filename: str
    created: datetime
    file_extension: str


class FileResponseByChatID(BaseSchema):
    lists: list[FilesDetailResponse]

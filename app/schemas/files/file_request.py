from uuid import UUID

from app.schemas.base import BaseSchema


class UploadFileRequest(BaseSchema):
    id: UUID
from app.schemas.base import BaseSchema


class FileDownloadRequest(BaseSchema):
    stored_file_id: str

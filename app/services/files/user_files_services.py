import os
from typing import Annotated
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, UploadFile
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.infrastructure.analytics_agent.azure_storage_manager import AzureBlobStorageManager
from app.models.maindb.file import File
from app.schemas.files.file_mapper import FileMapper
from app.schemas.files.file_response import FilesDetailResponse
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user

load_dotenv()


def save_file_id_to_db(session, file_id: UUID, file_name: str, blob_name: UUID, file_extension: str):
    new_file = File(id=file_id, file_name=file_name, blob_name=blob_name, file_extension=file_extension)
    session.add(new_file)
    session.commit()


class UserFileService:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ):
        self.session = session
        self.user = user
        self.blob_service = AzureBlobStorageManager(os.environ["AZURE_STORAGE_FILE_CONTAINER"])

    def upload_file(self, file: UploadFile) -> FilesDetailResponse:
        file_id = self.blob_service.upload_file(file)
        file_name = file.filename
        file_extension = file.content_type
        file_obj = File(file_name=file_name, blob_name=file_id, file_extension=file_extension)
        self.session.add(file_obj)
        self.session.commit()
        return FileMapper.map_to_file_response(file_obj)

    def upload_file_callback(self, file_path: str, file_id: UUID, file_extension: str, callback=None):
        with open(file_path, 'rb') as file:
            metadata = {"media_type": file_extension}
            blob_name = self.blob_service.blob_upload_file(file, metadata=metadata)
            file_name = os.path.basename(file_path)
            if callback:
                callback(self.session, file_id, file_name, blob_name, file_extension)
        os.remove(file_path)

    def download_file(self, file_id: UUID):
        return self.blob_service.download_pdf_file(file_id=file_id)

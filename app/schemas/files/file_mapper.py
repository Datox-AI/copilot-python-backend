from app.models.maindb import File
from app.schemas.files.file_response import FilesDetailResponse


class FileMapper:
    @staticmethod
    def map_to_file_response(
        file: File,
    ) -> FilesDetailResponse:
        return FilesDetailResponse(
            id=file.id, name=file.file_name, created=file.created_at, file_extension=file.file_extension
        )

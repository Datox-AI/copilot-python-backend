from typing import Annotated, List
from uuid import UUID
from fastapi.responses import StreamingResponse
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Response

from app.infrastructure.analytics_agent.azure_storage_manager import AzureBlobStorageManager
from app.schemas.files.file_response import FilesDetailResponse
from app.services.files.user_files_services import UserFileService

router = APIRouter(prefix="/api/files", tags=["Files"])


# @router.get("/chat/{chat_id}", response_model=List[str])  # Update response model as needed
# async def get_chat_files(
#     chat_id: str, blob_storage_service: AzureBlobStorageManager = Depends(get_blob_storage_service)
# ):
#     # Implement the logic to retrieve chat files
#     pass


@router.get("/download/{file_id}", status_code=status.HTTP_200_OK)
async def download_file(
    response: Response, file_id: UUID, file_download_service: Annotated[UserFileService, Depends()]
):
    try:
        file_data, media_type = file_download_service.download_file(file_id=file_id)
        file = io.BytesIO(file_data)
        return StreamingResponse(file, media_type=media_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")


@router.post("/files", response_model=FilesDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(file_upload_service: Annotated[UserFileService, Depends()], file: UploadFile = File(...)):
    try:
        return file_upload_service.upload_file(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")

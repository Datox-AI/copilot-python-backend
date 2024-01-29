from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.infrastructure.agent.azure_storage_manager import AzureBlobStorageManager
from app.schemas.files.file_request import UploadFileRequest
from app.schemas.files.file_response import FileResponseByChatID
from app.services.files.files_upload import FileUploadService

router = APIRouter(prefix="/api/files", tags=["Files"])


# Injecting BlobStorageService dependency
def get_blob_storage_service() -> AzureBlobStorageManager:
    return AzureBlobStorageManager("your_storage_connection_string", "your_container_name")


@router.get("/chat/{chat_id}", response_model=List[str])  # Update response model as needed
async def get_chat_files(
    chat_id: str, blob_storage_service: AzureBlobStorageManager = Depends(get_blob_storage_service)
):
    # Implement the logic to retrieve chat files
    pass


@router.get("/download/{file_id}", status_code=status.HTTP_200_OK)
async def download_file(
    file_id: str, blob_storage_service: AzureBlobStorageManager = Depends(get_blob_storage_service)
):
    try:
        file_data = blob_storage_service.download_file(file_id)
        return file_data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")


@router.post("/files", response_model=FileResponseByChatID, status_code=status.HTTP_201_CREATED)
async def upload_file(file_upload_service: Annotated[FileUploadService, Depends()], file: UploadFile = File(...)):
    try:
        return file_upload_service.upload_file(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")

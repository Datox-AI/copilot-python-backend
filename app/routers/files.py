from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.schemas.files.file_request import UploadFileRequest
from app.schemas.files.file_response import FileResponseByChatID


router = APIRouter(prefix="/api/files", tags=["Files"])


@router.get("/chat/{chat_id}", response_model=FileResponseByChatID, status_code=status.HTTP_201_CREATED)
async def create_chat(chat_id: UUID):
    return {"message": "Getted successfully."}

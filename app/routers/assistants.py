import uuid, io
import asyncio
from typing import Annotated, List
from uuid import UUID
import urllib 

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import create_engine

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from json.decoder import JSONDecodeError

from app.schemas.assistants import CreateAssistantSchema
from app.services.assistant import AssistantService


router = APIRouter(prefix="/api/assistants", tags=["Assistants"])


@router.post("/create-assistant")
async def create_assistant(
    request: CreateAssistantSchema,
    assistant_service: AssistantService
):
    if len(request.knowledge_files) > 40:
        raise HTTPException(status_code=400, detail="Max number of files must be 40")
    
    return assistant_service.create_assistant(request=request)



@router.post("/update-assistant-files")
async def update_message_files(
    assistant_id: int,
    files_to_delete: List[UUID] = Form(...),
    new_files: List[UploadFile] = File(None)
):
    # Example processing steps:
    # 1. Validate chat_id and message_id
    # 2. Delete files as specified
    # 3. Upload new files
    # 4. Update the database accordingly
    # 5. Respond with the updated file list
    pass


import io
from uuid import UUID
from typing import Annotated, List

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.schemas.assistants import CreateAssistantSchema, CreateAssistantMessageSchema, UpdateAssistantSchema
from app.services.messages import AssistantMessageService
from app.services.assistant import AssistantService

router = APIRouter(prefix="/api/assistants", tags=["Assistants"])


# Assistant routes
@router.get("/get-assistants")
async def get_assistants(assistant_service: Annotated[AssistantService, Depends()]):
    return assistant_service.get_assistants()


@router.get("/get-assistant/{assistant_id}")
async def get_assistant(
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_id: str
):
    return assistant_service.get_assistant(assistant_id=assistant_id)


@router.get("/download-icon/{icon_id}")
async def download_icon(
    assistant_service: Annotated[AssistantService, Depends()],
    icon_id: str
):
    try:
        file_data, media_type = await assistant_service.download_icon(icon_id=icon_id)
        file = io.BytesIO(file_data)
        return StreamingResponse(file, media_type=media_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Icon not found: {e}")


@router.post("/download-knowledge_file/{assistant_id}")
async def download_knowledge_file(
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_id: str,
    knowledge_blob_name: str = Form(...)
):
    file_data, media_type = await assistant_service.download_knowledge_file(
        assistant_id=assistant_id,
        knowledge_blob_name=knowledge_blob_name
    )
    file = io.BytesIO(file_data)
    return StreamingResponse(file, media_type=media_type)


@router.post("/create-assistant")
async def create_assistant(
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_name: str = Form(...),
    assistant_description: str = Form(...),
    assistant_instruction: str = Form(...),    
    icon: UploadFile = File(None),
    knowledge_files: List[UploadFile] = File(None),
):
    if knowledge_files is not None and len(knowledge_files) > 40:
        raise HTTPException(status_code=400, detail="Max number of files must be 40")
    
    request = CreateAssistantSchema(
        name=assistant_name,
        description=assistant_description,
        instruction=assistant_instruction
    )
    if knowledge_files is None:
        knowledge_files = []
    return await assistant_service.create_assistant(request=request, knowledge_files=knowledge_files, icon=icon)


@router.patch("/update-assistant/{assistant_id}")
async def update_assistant(
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_id: str,
    assistant_name: str = Form(None),
    assistant_description: str = Form(None),
    assistant_instruction: str = Form(None),
    icon: UploadFile = File(None)
):
    request = UpdateAssistantSchema(
        name=assistant_name,
        description=assistant_description,
        instruction=assistant_instruction
    )
    return await assistant_service.update_assistant(
        assistant_id=assistant_id, 
        request=request, 
        icon=icon
    )


@router.patch("/update-assistant-files/{assistant_id}")
async def update_assistant_files(
    assistant_id: str,
    assistant_service: Annotated[AssistantService, Depends()],
    files_to_delete: List[str] = Form(None),
    new_files: List[UploadFile] = File(None)
):
    print(files_to_delete, " files to delete")
    if files_to_delete == [""] or files_to_delete is None:
        files_to_delete = []
    if new_files is None:
        new_files = []
    return await assistant_service.update_assistant_files(
        assistant_id=assistant_id,
        files_to_delete=files_to_delete, 
        new_files=new_files
    )  


@router.delete("/delete-assistant/{assistant_id}")
def delete_assistant(
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_id: str
):
    return assistant_service.delete_assistant(assistant_id=assistant_id)


# Assistant message routes
@router.post("/{assistant_id}/chats/{chat_id}/messages")
async def create(
    assistant_message_service: Annotated[AssistantMessageService, Depends()],
    request: CreateAssistantMessageSchema,

):
    return assistant_message_service.create_user_message(
        request=request
    )

@router.get("/{assistant_id}/chats/{chat_id}/messages")
async def get(
    assistant_message_service: Annotated[AssistantMessageService, Depends()],    
):
    return assistant_message_service.get_user_message()
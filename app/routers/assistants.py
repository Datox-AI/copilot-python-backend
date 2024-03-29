import io, os
from uuid import UUID
from typing import Annotated, List

from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import StreamingResponse

from app.schemas.assistants import CreateAssistantSchema, CreateAssistantMessageSchema, UpdateAssistantSchema
from app.services.messages import AssistantMessageService
from app.services.assistant import AssistantService
from app.const import ICON_API_PATH, STATIC_FILES_DESTINATION


router = APIRouter(prefix="/api/assistants", tags=["Assistants"])


# Assistant routes
@router.get("/get-assistants")
async def get_assistants(
    request: Request,
    assistant_service: Annotated[AssistantService, Depends()]
):
    download_icon_api_url = _get_icon_path(request=request)
    
    return assistant_service.get_assistants(download_icon_api_url=download_icon_api_url)


@router.get("/get-assistant/{assistant_id}")
async def get_assistant(
    request: Request,
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_id: str
):
    download_icon_api_url = _get_icon_path(request=request)
    
    return assistant_service.get_assistant(assistant_id=assistant_id, download_icon_api_url=download_icon_api_url)


@router.get("/icons/{icon_id}")
async def get_icon(
    icon_id: str
):
    file_path = os.path.join(STATIC_FILES_DESTINATION, "assistant_icons", icon_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Icon file not found")
    print(file_path, " file path")
    return FileResponse(path=file_path)



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
    request: Request,
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_name: str = Form(...),
    assistant_description: str = Form(...),
    assistant_instruction: str = Form(...),    
    icon: UploadFile = File(None),
    knowledge_files: List[UploadFile] = File(None),
):    
    download_icon_api_url = _get_icon_path(request=request)
    if knowledge_files is not None and len(knowledge_files) > 40:
        raise HTTPException(status_code=400, detail="Max number of files must be 40")
    request_schema = CreateAssistantSchema(
        name=assistant_name,
        description=assistant_description,
        instruction=assistant_instruction
    )
    if knowledge_files is None:
        knowledge_files = []
    return await assistant_service.create_assistant(
        request_schema=request_schema, 
        knowledge_files=knowledge_files, 
        icon=icon, 
        download_icon_api_url=download_icon_api_url
    )


@router.patch("/update-assistant/{assistant_id}")
async def update_assistant(
    request: Request,
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_id: str,
    assistant_name: str = Form(None),
    assistant_description: str = Form(None),
    assistant_instruction: str = Form(None),
    icon: UploadFile = File(None)
):
    download_icon_api_url = _get_icon_path(request=request)
    
    request_schema = UpdateAssistantSchema(
        name=assistant_name,
        description=assistant_description,
        instruction=assistant_instruction
    )
    return await assistant_service.update_assistant(
        assistant_id=assistant_id, 
        request_schema=request_schema, 
        icon=icon,
        download_icon_api_url=download_icon_api_url
    )


@router.patch("/update-assistant-files/{assistant_id}")
async def update_assistant_files(
    request: Request,
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
    download_icon_api_url = _get_icon_path(request=request)
    
    return await assistant_service.update_assistant_files(
        assistant_id=assistant_id,
        files_to_delete=files_to_delete, 
        new_files=new_files,
        download_icon_api_url=download_icon_api_url
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




def _get_icon_path(request: Request):
    return f"{request.url.scheme}://{request.url.netloc}/{ICON_API_PATH}"
    
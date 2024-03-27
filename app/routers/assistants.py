from typing import Annotated, List

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.schemas.assistants import CreateAssistantSchema, AssistantResponseSchema
from app.services.assistant import AssistantService


router = APIRouter(prefix="/api/assistants", tags=["Assistants"])


@router.post("/create-assistant")
async def create_assistant(
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_name: str = Form(...),
    assistant_description: str = Form(...),
    assistant_instruction: str = Form(...),    
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
    return await assistant_service.create_assistant(request=request, knowledge_files=knowledge_files)



@router.get("/get-assistants")
async def get_assistants(assistant_service: Annotated[AssistantService, Depends()]):
    return assistant_service.get_assistants()

@router.get("/get-assistant-chats/{assistant_id}")
async def get_assistant_chats(
    assistant_service: Annotated[AssistantService, Depends()],
    assistant_id: str
):
    return assistant_service.get_assistant_chats(assistant_id=assistant_id)

@router.patch("/update-assistant-files/{assistant_id}")
async def update_message_files(
    assistant_id: str,
    assistant_service: Annotated[AssistantService, Depends()],
    files_to_delete: List[str] = Form(None),
    new_files: List[UploadFile] = File(None)
):
    print(files_to_delete, " files to delete")
    if files_to_delete == [""]:
        files_to_delete = []
    if new_files is None:
        new_files = []
    return await assistant_service.update_assistant_files(
        assistant_id=assistant_id,
        files_to_delete=files_to_delete, 
        new_files=new_files
    )  


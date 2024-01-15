from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from uuid import UUID
from typing import Annotated, List
from app.schemas.chat.chat_request import UpdateChatRequest
from app.schemas.identity.current_user import CurrentUser
from app.services.chats import (
    CreateChat,
    DeleteChat,
    GetChat
)
from app.schemas.chat import ChatResponse, CreateChatRequest
from app.services.chats.generate_chat_name import GenerateChatName
from app.services.chats.update_chat import UpdateChat
from app.shared.auth import current_user

router = APIRouter(prefix="/api/chats", tags=["Chats"])

@router.get("/", response_model=List[ChatResponse])
async def get_chats(get_chats_service: Annotated[GetChat, Depends()]):
    return get_chats_service.invoke()

@router.get("/{user_id}", response_model=List[ChatResponse])
async def get_chats_for_user(user_id: UUID, get_chats_service: Annotated[GetChat, Depends()], user: Annotated[CurrentUser, Depends(current_user)]):
    if "Admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    return get_chats_service.invoke(user_id)

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(request: CreateChatRequest, create_chat_service: Annotated[CreateChat, Depends()]):
    if request is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
    return create_chat_service.invoke(request)

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: UUID, delete_chat_service: Annotated[DeleteChat, Depends()]):
    delete_chat_service.invoke(chat_id)
    return {"message": "Chat deleted successfully."}

@router.put("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_chat(
    chat_id: UUID, 
    request: UpdateChatRequest, 
    update_chat_service: Annotated[UpdateChat, Depends()]
):
    if chat_id != request.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mismatched chat ID")

    update_chat_service.invoke(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.put("/{chat_id}/generate-name", response_model=str, status_code=status.HTTP_200_OK)
async def generate_chat_name(chat_id: UUID, generate_chat_name_service: Annotated[GenerateChatName, Depends()]):
    generated_name = generate_chat_name_service.invoke(chat_id)
    return generated_name
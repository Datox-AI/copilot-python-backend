from fastapi import APIRouter, Depends, HTTPException, Security, status
from uuid import UUID
from typing import Annotated, List
from app.services.chats import (
    CreateChat,
    DeleteChat,
    GetChat
)
from app.schemas.chat import ChatResponse, CreateChatRequest
from app.shared.auth import multi_auth, azure_scheme
from fastapi_azure_auth.user import User

router = APIRouter(prefix="/chats")

@router.get("/", response_model=List[ChatResponse])
async def get_chats(user_id: UUID, get_chats_service: Annotated[GetChat, Depends()]):
    return await get_chats_service.invoke(user_id)

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(request: CreateChatRequest, create_chat_service: Annotated[CreateChat, Depends()]):
    if request is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
    return await create_chat_service.invoke(request)

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: UUID, delete_chat_service: Annotated[DeleteChat, Depends()]):
    await delete_chat_service.invoke(chat_id)
    return {"message": "Chat deleted successfully."}

@router.get("/user",  response_model=User)
async def get_uesr(user: Annotated[User, Depends(azure_scheme)]):
    return user
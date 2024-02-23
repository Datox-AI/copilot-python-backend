from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.users.users_response import ApplicationUserRoleSchema, ApplicationUserSchema
from app.services.users import ApplicationUserService

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=List[ApplicationUserSchema])
async def get_application_users(user_service: ApplicationUserService = Depends(ApplicationUserService)):
    return user_service.get_users()


@router.get("/roles", response_model=List[ApplicationUserRoleSchema])
async def get_application_users_role(user_service: ApplicationUserService = Depends(ApplicationUserService)):
    return user_service.get_roles()


@router.get("/{user_id}/get_roles/")
async def user_get_roles(user_id: UUID, user_service: ApplicationUserService = Depends(ApplicationUserService)):
    try:
        roles = await user_service.get_user_roles(user_id)
        return roles
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

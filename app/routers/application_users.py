from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends

from app.schemas.users.users_response import ApplicationUserRoleSchema, ApplicationUserSchema
from app.services.users import ApplicationUserService
from app.schemas.users import UserRoleUpdateRequest

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=List[ApplicationUserSchema])
async def get_application_users(user_service: ApplicationUserService = Depends(ApplicationUserService)):
    return user_service.get_users()


@router.get("/roles", response_model=List[ApplicationUserRoleSchema])
async def get_application_users_role(user_service: ApplicationUserService = Depends(ApplicationUserService)):
    return await user_service.get_user_roles()


@router.put("/update_user_roles")
async def update_user_roles(request: UserRoleUpdateRequest, user_service: ApplicationUserService = Depends()):
    await user_service.update_user_roles_for_user(request.user_id, request.role_ids)
    return {"message": "User roles updated successfully"}

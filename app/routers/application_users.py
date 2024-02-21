from typing import List

from fastapi import APIRouter, Depends

from app.schemas.users.users_response import ApplicationUserRoleSchema, ApplicationUserSchema
from app.services.users import ApplicationUserService

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=List[ApplicationUserSchema])
async def get_application_users(user_service: ApplicationUserService = Depends(ApplicationUserService)):
    return user_service.get_users()


@router.get("/roles", response_model=List[ApplicationUserRoleSchema])
async def get_application_users_role(user_service: ApplicationUserService = Depends(ApplicationUserService)):
    return user_service.get_roles()

import uuid
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.backend.session import create_admindb_session
from app.models.admindb import (
    Tenant, 
    ApplicationUser,
    Role,
    UserRole
)

from app.schemas.identity.current_user import CurrentUser
from app.schemas.identity.current_user_request import CurrentUserRequest

class CheckUpdateUser:
    def __init__(self, session: Annotated[Session, Depends(create_admindb_session)]) -> None:
        self.session = session
        
    async def invoke(self, model: CurrentUserRequest) -> CurrentUser:
        # Check if the tenant exists
        print(self.session.execute(select(Tenant)).all(), " all")
            # print(row, " row")
        existing_tenant = self.session.execute(select(Tenant).where(Tenant.azure_object_id == model.tenant_id))
        # print(existing_tenant.scalars().all(), ' existsing tenatn')
        existing_tenant = existing_tenant.scalars().first()
        if not existing_tenant:
            raise HTTPException(401, "Tenant is not recognized or authorized.")

        # Check if the user exists
        user = await self.session.execute(select(ApplicationUser).where(ApplicationUser.azure_object_id == model.azure_object_id))
        user = user.scalars().first()
        
        name_parts = model.name.split()
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        if not user:
            # Create new user if not exists
            user = ApplicationUser(
                AzureObjectId=model.azure_object_id,
                TenantId=existing_tenant.Id,
                FirstName=first_name,
                LastName=last_name,
                Id=uuid.uuid4()
            )
            self.session.add(user)
        elif user.TenantId != existing_tenant.Id:
            raise HTTPException(401, "Tenant is not recognized or authorized.")

        await self.session.commit()

        # Manage roles
        default_roles = ["Admin", "User"]
        for role_name in default_roles:
            role = await self.session.execute(select(Role).where(Role.Name == role_name))
            role = role.scalars().first()
            if not role:
                role = Role(Id=uuid.uuid4(), Name=role_name)
                self.session.add(role)

        await self.session.commit()

        for role_name in model.roles:
            if role_name in default_roles:
                role = await self.session.execute(select(Role).where(Role.Name == role_name))
                role = role.scalars().first()
                if not any(user_role.RoleId == role.Id for user_role in user.UserRoles):
                    user_role = UserRole(UserId=user.Id, RoleId=role.Id)
                    self.session.add(user_role)

        await self.session.commit()

        return CurrentUser(
            CurrentRoles=model.roles,
            CurrentTenantId=user.tenant_id,
            CurrentUserAzureObjectId=user.azure_object_id,
            CurrentUserId=user.id,
            CurrentUserName=model.name
        )
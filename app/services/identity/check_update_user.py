import uuid
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.backend.session import create_admindb_session
from app.models.admindb import Tenant, ApplicationUser, Role, UserRole

from app.schemas.identity.current_user import CurrentUser
from app.schemas.identity.current_user_request import CurrentUserRequest


class CheckUpdateUser:
    def __init__(
        self, session: Annotated[Session, Depends(create_admindb_session)]
    ) -> None:
        self.session = session

    async def invoke(self, model: CurrentUserRequest) -> CurrentUser:

        existing_tenant = self.session.execute(
            select(Tenant).where(Tenant.azure_object_id == model.tenant_id)
        )
        existing_tenant = existing_tenant.scalars().first()
        if not existing_tenant:
            raise HTTPException(401, "Tenant is not recognized or authorized.")

        # Check if the user exists
        user = self.session.execute(
            select(ApplicationUser).where(
                ApplicationUser.azure_object_id == model.azure_object_id
            )
        )
        user = user.scalars().first()

        name_parts = model.name.split()
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        if not user:
            # Create new user if not exists
            user = ApplicationUser(
                azure_object_id=model.azure_object_id,
                tenant_id=existing_tenant.id,
                first_name=first_name,
                last_name=last_name,
                id=uuid.uuid4(),
            )
            self.session.add(user)
        elif user.tenant_id != existing_tenant.id:
            raise HTTPException(401, "Tenant is not recognized or authorized.")

        self.session.commit()

        # Manage roles
        default_roles = ["Admin", "User"]
        for role_name in default_roles:
            role = self.session.execute(select(Role).where(Role.name == role_name))
            role = role.scalars().first()
            if not role:
                role = Role(id=uuid.uuid4(), name=role_name)
                self.session.add(role)

        self.session.commit()

        for role_name in model.roles:
            if role_name in default_roles:
                role = self.session.execute(select(Role).where(Role.name == role_name))
                role = role.scalars().first()
                if not any(
                    user_role.role_id == role.id for user_role in user.user_roles
                ):
                    user_role = UserRole(user_id=user.id, role_id=role.id)
                    self.session.add(user_role)

        self.session.commit()

        return CurrentUser(
            roles=model.roles,
            tenant_id=user.tenant_id,
            azure_object_id=user.azure_object_id,
            user_id=user.id,
            user_name=model.name,
        )

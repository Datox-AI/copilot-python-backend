import json
import uuid
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.session import create_admindb_session
from app.models.admindb import ApplicationUser, Role
from app.schemas.identity.current_user import CurrentUser
from app.schemas.users import ApplicationUserMapper
from app.shared.auth.azure_scheme import current_user


class ApplicationUserService:
    def __init__(
        self,
        user: Annotated[CurrentUser, Depends(current_user)],
        session: Annotated[Session, Depends(create_admindb_session)],
    ) -> None:
        self.session = session
        self.user = user

    def get_users(self):
        application_users = self.session.query(ApplicationUser).all()
        return [ApplicationUserMapper.map_to_application_user_response(user) for user in application_users]

    def get_roles(self):
        application_user_roles = self.session.query(Role).all()
        return [ApplicationUserMapper.map_to_application_user_role_response(role) for role in application_user_roles]

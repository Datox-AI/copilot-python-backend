from pydantic import Field
from typing import List, Optional
from uuid import UUID

from app.schemas.base import BaseSchema


class ApplicationUserRoleSchema(BaseSchema):
    id: UUID
    name: str
    azure_role_id: Optional[str] = Field(None, description="Azure Role ID associated with the role")


class AzureUserRoleSchema(BaseSchema):
    azure_role_id: UUID
    name: str


class ApplicationUserSchema(BaseSchema):
    id: UUID
    azure_object_id: str
    first_name: str
    last_name: str
    roles: List[ApplicationUserRoleSchema] = []

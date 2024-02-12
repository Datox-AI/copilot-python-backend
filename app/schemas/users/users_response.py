from typing import List
from uuid import UUID

from app.schemas.base import BaseSchema


class ApplicationUserRoleSchema(BaseSchema):
    id: UUID
    name: str


class ApplicationUserSchema(BaseSchema):
    id: UUID
    azure_object_id: str
    first_name: str
    last_name: str
    roles: List[ApplicationUserRoleSchema] = []

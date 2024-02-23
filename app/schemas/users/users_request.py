from typing import List
from uuid import UUID
from app.schemas.base import BaseSchema


class UserRoleUpdateRequest(BaseSchema):
    user_id: UUID
    role_ids: List[UUID]

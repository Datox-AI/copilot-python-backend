from typing import List, Optional
from app.enums.user_enums import UserStatus
from app.schemas.base import BaseSchema
from uuid import UUID

from app.schemas.users.azure_user import AppRoles

class UserResponse(BaseSchema):
    id: Optional[UUID]
    ad_id: str
    display_name: str
    roles: List[AppRoles] = []
    status: UserStatus
    chats_count: int
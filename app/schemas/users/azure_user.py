
from typing import List
from uuid import UUID

from app.schemas.base import BaseSchema

class AppRoles(BaseSchema):
    id: UUID
    name: str

class AzureUser(BaseSchema):
    id: str
    display_name: str
    roles: List[AppRoles] = []
    

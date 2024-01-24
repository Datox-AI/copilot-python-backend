from typing import Optional, List
from pydantic import BaseModel, UUID4


class CurrentUser(BaseModel):
    user_id: Optional[UUID4]
    tenant_id: Optional[UUID4]
    user_name: Optional[str]
    roles: Optional[List[str]]
    azure_object_id: Optional[str]

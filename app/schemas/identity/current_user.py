from typing import List, Optional

from pydantic import UUID4, BaseModel


class CurrentUser(BaseModel):
    user_id: Optional[UUID4]
    tenant_id: Optional[UUID4]
    user_name: Optional[str]
    roles: Optional[List[str]]
    azure_object_id: Optional[str]

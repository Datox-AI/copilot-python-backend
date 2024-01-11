from typing import Optional, List
from pydantic import BaseModel, UUID4

class CurrentUser(BaseModel):
    CurrentUserId: Optional[UUID4]
    CurrentTenantId: Optional[UUID4]
    CurrentUserName: Optional[str]
    CurrentRoles: Optional[List[str]]
    CurrentUserAzureObjectId: Optional[str]
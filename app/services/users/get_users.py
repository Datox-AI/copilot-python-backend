from typing import Annotated, List, Optional
from fastapi import Depends
from sqlalchemy.orm import Session

from app.backend.session import create_admindb_session, create_maindb_session
from app.enums.user_enums import UserStatus
from app.schemas.identity.current_user import CurrentUser
from app.schemas.users.user_response import UserResponse
from app.shared.auth.azure_scheme import current_user


class GetUsers:
    def __init__(self, session: Annotated[Session, Depends(create_admindb_session)],
                 user: Annotated[CurrentUser, Depends(current_user)]) -> None:
        self.session = session
        self.user = user
        
    async def get_users(self, user_statuses: Optional[List[UserStatus]] = None) -> List[UserResponse]:
        
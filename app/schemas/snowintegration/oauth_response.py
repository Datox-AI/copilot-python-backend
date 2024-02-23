from uuid import UUID
from typing import Union
from app.schemas.base import BaseSchema


class SnowflakeIdentifierResponse(BaseSchema):
    id: UUID
    account_identifier: str
    client_id: str
    client_secret: str
    token_endpoint: str
    user_role: Union[str, None]
    warehouse: str
    authorization_url: str

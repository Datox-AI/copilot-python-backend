from uuid import UUID

from app.schemas.base import BaseSchema


class SnowflakeIdentifierResponse(BaseSchema):
    id: UUID
    account_identifier: str
    client_id: str
    client_secret: str
    token_endpoint: str
    user_role: str
    warehouse: str
    authorization_url: str

from app.schemas.base import BaseSchema


# Pydantic model for OAuth configuration
class OAuthConfig(BaseSchema):
    account_identifier: str
    client_id: str
    client_secret: str
    token_endpoint: str
    warehouse: str | None


class Warehouse(BaseSchema):
    name: str

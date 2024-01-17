from app.schemas.base import BaseSchema


class CurrentUserRequest(BaseSchema):
    azure_object_id: str
    tenant_id: str
    name: str
    roles: list

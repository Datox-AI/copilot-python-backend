from app.schemas.base import BaseSchema


class AgentRequest(BaseSchema):
    query: str
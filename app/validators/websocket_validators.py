import asyncio
import uuid

from sqlalchemy.orm import Session

from app.enums import ChatType
from app.models.maindb import Chat
from app.services.identity import CheckUpdateUser
from app.shared.auth.azure_scheme_for_socket import validate_azure_token


class DataAnalyticAgentWebsocketValidator:
    def __init__(self, token: str, chat_id: uuid.UUID, maindb_session: Session, check_update_user: CheckUpdateUser):
        self.token = token
        self.chat_id = chat_id
        self.maindb_session = maindb_session
        self.check_update_user = check_update_user

        # errors
        self.error_message = None

    async def validate(self):
        is_valid = False
        if self.token == "":
            self.error_message = "Token query is required"
            return is_valid
        # checking chat
        self.chat_obj = self.maindb_session.query(Chat).filter(Chat.id == self.chat_id).first()
        if not self.chat_obj:
            self.error_message = f"Chat object under {self.chat_id} id does not exist"
            return is_valid
        if self.chat_obj.type != ChatType.DataAnalytics:
            self.error_message = (
                f"Chat object under {self.chat_id} id does not have {ChatType.DataAnalytics.value} chat type"
            )
            return is_valid
        # checking token
        self.validated_user, token_error_message = await validate_azure_token(
            access_token=self.token, check_update_user=self.check_update_user
        )
        if not self.validated_user:
            self.error_message = token_error_message
            return is_valid
        # everything is clean (although code isn't)
        is_valid = True
        return is_valid

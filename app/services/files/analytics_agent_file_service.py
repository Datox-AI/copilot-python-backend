import os
from typing import Annotated
from uuid import UUID

import pandas as pd
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.enums.chat_enums import ChatType
from app.infrastructure.analytics_agent.azure_storage_manager import AzureBlobStorageManager
from app.models.maindb.chat import Chat
from app.models.maindb.message import Message
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user


class AnalyticsAgentFileService:
    def __init__(
        self,
        chat_id: UUID,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ):
        self.user = user
        self.chat_id = chat_id
        self.session = session
        self.blob_service = AzureBlobStorageManager(os.environ["AZURE_STORAGE_DA_AGENT_CONTAINER"])
        self._check_chat_id()

    def _check_chat_id(self):
        chat_obj = self.session.query(Chat).filter(Chat.id == self.chat_id).first()
        if not chat_obj:
            raise HTTPException(status_code=404, detail=f"Chat object under {self.chat_id} id does not exist")
        if chat_obj.type != ChatType.DataAnalytics:
            raise HTTPException(
                status_code=400,
                detail=f"Chat object under {self.chat_id} id does not have FileSearch as its chat type",
            )
    
    def download_file(self, stored_file_id: str):
        chat_message_with_store_id = (
            self.session.query(Message)
            .filter(Message.chat_id == self.chat_id, Message.stored_file_id == stored_file_id)
            .first()
        )
        if chat_message_with_store_id:
            return self.blob_service.download_csv_file(stored_file_id=stored_file_id)
        else:
            raise HTTPException(status_code=404, detail=f"File with store id ({stored_file_id}) not found")

    def get_csv_data(self, stored_file_id):
        chat_message_with_store_id = (
            self.session.query(Message)
            .filter(Message.chat_id == self.chat_id, Message.stored_file_id == stored_file_id)
            .first()
        )
        if chat_message_with_store_id:
            downloaded_stream = self.blob_service.download_csv_file(stored_file_id=stored_file_id)[0]
            df = pd.read_csv(downloaded_stream)
            df_data = df.to_dict(orient="records")
            return df_data
        else:
            raise HTTPException(status_code=404, detail=f"File with store id ({stored_file_id}) not found")
    
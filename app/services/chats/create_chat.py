import os 
import uuid
from typing import Annotated
from dotenv import load_dotenv

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from openai import AzureOpenAI

from app.backend.session import create_maindb_session
from app.models.maindb import Chat, ChatSnowflakeData, Assistant
from app.enums.chat_enums import ChatType
from app.schemas.chat import ChatMapper, ChatResponse, CreateChatRequest
from app.schemas.identity.current_user import CurrentUser
from app.shared.auth.azure_scheme import current_user

load_dotenv(override=True)

class CreateChat:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_maindb_session)],
        user: Annotated[CurrentUser, Depends(current_user)],
    ) -> None:
        self.session = session
        self.user = user

    def invoke(self, model: CreateChatRequest) -> ChatResponse:
        new_chat = Chat(id=uuid.uuid4(), name="New Chat", type=model.type)
        if model.snowflake_data and model.type == ChatType.DataAnalytics:
            snowflake_data = ChatSnowflakeData(
                id=uuid.uuid4(),
                snowflake_account=model.snowflake_data.snowflake_account,
                database_name=model.snowflake_data.database_name,
                schema=model.snowflake_data.snowflake_schema,
                warehouse=model.snowflake_data.warehouse,
            )
            new_chat.snowflake_data = snowflake_data
            
        if model.assistant_id and model.type == ChatType.Assistant:
            # checking assistant id 
            assistant_obj = self.session.query(Assistant).filter(Assistant.assistant_id == model.assistant_id, Assistant.created_by == self.user.user_id).first()
            if assistant_obj is None:
                raise HTTPException(status_code=404, detail=f"Assistant object under {model.assistant_id} id does not exist")
            client = AzureOpenAI(
                azure_endpoint=os.environ.get("GPT4_TURBO_AZURE_OPENAI_ENDPOINT"),
                api_key=os.environ.get("GPT4_TURBO_AZURE_OPENAI_API_KEY"),
                api_version=os.environ.get("GPT4_ASSISTANT_OPENAI_API_VERSION"),
            )
            # creating thread for chat
            try:
                thread = client.beta.threads.create()
            except Exception as e:
                print(f"thread creation failed: {e}")
                raise HTTPException(detail=f"thread creation failed: {e}", status_code=500)
            #assigning assistant and thread id 
            new_chat.assistant = assistant_obj
            new_chat.assistant_thread_id = thread.id
            

        self.session.add(new_chat)
        self.session.commit()

        return ChatMapper.map_to_chat_response(new_chat, 0, 0)

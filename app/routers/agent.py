import json
import uuid
from typing import Annotated
from uuid import UUID

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query, Security, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.infrastructure.agent.agent_service import AgentSnowflakeEngineManager, DataAnalyticAgent
from app.models.maindb.message import Message
from app.mysocket.connection import ConnectionManager
from app.services.chats import GetChat
from app.services.identity import CheckUpdateUser
from app.services.messages import MessageService
from app.shared.auth import azure_scheme, multi_auth
from app.shared.auth.azure_scheme_for_socket import validate_azure_token

load_dotenv()

router = APIRouter(prefix="/agent")
manager = ConnectionManager()


@router.websocket("/ws/{chat_id}")
async def agent_endpoint(
    chat_id: UUID,
    websocket: WebSocket,
    check_update_user: Annotated[CheckUpdateUser, Depends()],
    maindb_session: Annotated[Session, Depends(create_maindb_session)],
    token: str = Query(...),
):
    await manager.connect(websocket=websocket)
    # checking token
    if token:
        user, error_message = await validate_azure_token(token, check_update_user=check_update_user)
        if user:
            # initiating agent and message service classes
            agent_engine_manager = AgentSnowflakeEngineManager()
            message_service = MessageService(user=user, chat_id=chat_id, session=maindb_session)
            # default connection engine error
            connection_error_message = "Engine is not connected"
            try:
                while True:
                    # checking whether engine is alive
                    if not agent_engine_manager.is_engine_alive():
                        await manager.send_error_message(message=connection_error_message, websocket=websocket)
                        # await websocket.send_json({"status": connection_error_message})
                        snowflake_data = await websocket.receive_json()
                        is_valid, error_message = agent_engine_manager.create_engine(snowflake_data)
                        if not is_valid:
                            connection_error_message = f"Failed to establish database connection: {error_message}"
                            continue
                        # notifying front end about connection is succesful
                        await manager.send_connection_success_message(websocket=websocket)
                        # Initialize the agent only if it's not already initialized or if the engine was recreated
                        agent = DataAnalyticAgent(
                            snowflake_engine=agent_engine_manager.engine,
                            chat_id=chat_id,
                            db_session=maindb_session,
                        )
                        # changing connection error message to default in case engine needs to reconnect
                        connection_error_message = "Engine is not connected"

                    # chatting process
                    user_input = await websocket.receive_text()
                    # invoking agent
                    agent_message_id = uuid.uuid4()
                    agent_response, is_agent_response_valid = await agent.invoke(
                        user_query=user_input, message_id=agent_message_id
                    )
                    if is_agent_response_valid:
                        # saving user and agent responses
                        message_service.create_user_message(message_text=user_input)
                        message_service.create_agent_response(
                            message_id=agent_message_id,
                            agent_final_output=agent_response["output"],
                            sql_query=agent_response["sql_query"],
                            stored_file_id=agent_response["stored_file_id"],
                            follow_up_questions=agent_response["followup_questions"],
                        )
                        await manager.send_agent_response(response=agent_response, websocket=websocket)
                    else:
                        await manager.send_error_message(message="Agent failed!", websocket=websocket)

            except WebSocketDisconnect:
                await manager.disconnect(websocket=websocket, closed=True)

        else:
            await manager.disconnect(websocket=websocket, code=1007, reason=error_message.value)
    else:
        await manager.disconnect(websocket=websocket, code=1007, reason="Token query is required")

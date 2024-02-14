import uuid
from typing import Annotated
from uuid import UUID

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.backend.session import create_maindb_session
from app.infrastructure.analytics_agent.agent_service import AgentSnowflakeEngineManager, DataAnalyticAgent
from app.mysocket.connection import ConnectionManager
from app.services.identity import CheckUpdateUser
from app.services.messages.analytics_agent.message_service import AnalyticsAgentMessageCreateService
from app.services.files.analytics_agent_file_service import AnalyticsAgentFileService
from app.validators.websocket_validators import DataAnalyticAgentWebsocketValidator
from app.schemas.data_analytics_agent.agent_request import FileDownloadRequest


load_dotenv()

router = APIRouter(prefix="/api/analytics_agent", tags=["Data analytics agent"])

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
    # validating token, and chat_id
    validator = DataAnalyticAgentWebsocketValidator(
        chat_id=chat_id, token=token, maindb_session=maindb_session, check_update_user=check_update_user
    )
    is_valid = await validator.validate()
    print(validator.error_message, " --- validation error")
    if is_valid:
        # getting the validated user from validator
        user = validator.validated_user
        chat_obj = validator.chat_obj
        # initiating services
        agent_engine_manager = AgentSnowflakeEngineManager()
        message_service = AnalyticsAgentMessageCreateService(user=user, chat_id=chat_id, session=maindb_session)
        # default connection engine error
        connection_error_message = "Engine is not connected"
        try:
            while True:
                # checking whether engine is alive
                if not agent_engine_manager.is_engine_alive():
                    await manager.send_error_message(message=connection_error_message, websocket=websocket)
                    # await websocket.send_json({"status": connection_error_message})
                    snowflake_token_data = await websocket.receive_json()
                    print(type(snowflake_token_data), snowflake_token_data, " ------ received snowflake data")
                    is_valid, error_message = agent_engine_manager.create_engine(
                        snowflake_token_data=snowflake_token_data, chat_obj=chat_obj
                    )
                    if not is_valid:
                        connection_error_message = f"Failed to establish database connection: {error_message}"
                        print(connection_error_message)
                        continue
                    # Initialize the agent only if it's not already initialized or if the engine was recreated

                    try:
                        agent = DataAnalyticAgent(
                            snowflake_engine=agent_engine_manager.engine,
                            chat_id=chat_id,
                            db_session=maindb_session,
                        )
                    except Exception as e:
                        print(e, "   agent error")
                        error_message = f"Agent failed: {e}"
                        await manager.disconnect(websocket=websocket, reason=error_message, code=1007)
                        break
                    # notifying front end about connection is succesful
                    await manager.send_connection_success_message(websocket=websocket)
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
        await manager.disconnect(websocket=websocket, code=1007, reason=validator.error_message)


@router.get("/{chat_id}/messages")
async def get_messages(
    chat_id: UUID,
    get_message_service: Annotated[AnalyticsAgentMessageCreateService, Depends()],
):
    # return None
    return get_message_service.get_messages()


@router.post("/{chat_id}/get_stored_data")
async def get_stored_data(
    chat_id: UUID, request: FileDownloadRequest, file_service: Annotated[AnalyticsAgentFileService, Depends()]
):
    return file_service.download_file(request.stored_file_id)

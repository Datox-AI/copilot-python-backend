from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, Security
from dotenv import load_dotenv
from typing import Annotated
from uuid import UUID
from sqlalchemy.orm import Session

from app.shared.auth.azure_scheme_for_socket import validate_azure_token
from app.mysocket.connection import ConnectionManager
from app.infrastructure.agent.agent_service import (
    DataAnalyticAgent,
    AgentSnowflakeEngineManager,
)
from app.services.messages import MessageService
from app.shared.auth import multi_auth, azure_scheme
from app.services.chats import GetChat
from app.services.identity import CheckUpdateUser
from app.backend.session import create_maindb_session


load_dotenv()

router = APIRouter(prefix="/agent")
manager = ConnectionManager()


# @router.get("/test")
# async def test(get_chat_service: Annotated[GetChat, Depends()]):
#     return


# @router.get("/message_history{chat_id}")
@router.websocket("/test/{chat_id}")
async def test_ws(
    chat_id: UUID,
    websocket: WebSocket,
    check_update_user: Annotated[CheckUpdateUser, Depends()],
    session: Annotated[Session, Depends(create_maindb_session)],
    token: str = Query(...),
):
    await manager.connect(websocket=websocket)
    # is_valid, error_message
    if token:
        user, error_message = await validate_azure_token(
            token, check_update_user=check_update_user
        )
        if user:
            message_service = MessageService(
                user=user, chat_id=chat_id, session=session
            )
            await websocket.send_text("ready")

            # try:
            while True:
                data = await websocket.receive_text()
                message_response = message_service.create_user_message(
                    message_text=data
                )
                print(message_response)
                await websocket.send_json(message_response)
            # except Exception as e:
            #     print(e)
            #     await manager.disconnect(websocket=websocket)
        else:
            print(f"merror message -- {error_message.value}")
            await manager.disconnect(
                websocket=websocket, code=1007, reason=error_message.value
            )
    else:
        await manager.disconnect(
            websocket=websocket, code=1007, reason="Token query is required"
        )


@router.websocket("/ws")
async def agent_endpoint(websocket: WebSocket):
    websocket.headers()
    await manager.connect(websocket=websocket)
    websocket.headers
    agent_engine_manager = AgentSnowflakeEngineManager()
    # default connection engine error
    connection_error_message = "Engine is not connected"

    try:
        while True:
            if not agent_engine_manager.is_engine_alive():
                await manager.send_connection_error_message(
                    message=connection_error_message, websocket=websocket
                )
                # await websocket.send_json({"status": connection_error_message})
                snowflake_data = await websocket.receive_json()
                is_valid, error_message = agent_engine_manager.create_engine(
                    snowflake_data
                )
                if not is_valid:
                    connection_error_message = (
                        f"Failed to establish database connection: {error_message}"
                    )
                    continue
                # notifying front end about connection is succesful
                await manager.send_connection_success_message(websocket=websocket)
                # Initialize the agent only if it's not already initialized or if the engine was recreated
                agent = DataAnalyticAgent(snowflake_engine=agent_engine_manager.engine)
                # changing connection error message to default in case engine needs to reconnect
                connection_error_message = "Engine is not connected"

            # chatting with user
            user_input = await websocket.receive_text()
            response = await agent.invoke(user_query=user_input)
            await manager.send_agent_response(response=response, websocket=websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

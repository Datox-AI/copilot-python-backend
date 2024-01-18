from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, Security
from dotenv import load_dotenv
from typing import Annotated
from uuid import UUID
import uuid
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
from app.models.maindb.message import Message
import json 


load_dotenv()

router = APIRouter(prefix="/agent")
manager = ConnectionManager()


# @router.get("/test")
# async def test(get_chat_service: Annotated[GetChat, Depends()]):
#     return


@router.get("/test")
async def test_api(
    maindb_session: Annotated[Session, Depends(create_maindb_session)],
):
    query = maindb_session.query(
        Message.text, 
        Message.role, 
        Message.sql_query
    ).filter(Message.chat_id == "cd229392-a310-4212-82f0-c5cb7b1e1b10").order_by(Message.created_at)
    messages = query.all()
    print(messages[0].text)
    print(messages[1].text)

    # print(json.loads(messages[0]))
    


@router.websocket("/test/{chat_id}")
async def test_ws(
    chat_id: UUID,
    websocket: WebSocket,
    check_update_user: Annotated[CheckUpdateUser, Depends()],
    maindb_session: Annotated[Session, Depends(create_maindb_session)],
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
                user=user, chat_id=chat_id, session=maindb_session
            )
            await websocket.send_text("ready")

            # try:
            while True:
                data = await websocket.receive_text()
                message_response = message_service.create_user_message(
                    message_text=data
                )
                await websocket.send_json(message_response)
            # except Exception as e:
            #     print(e)
            #     await manager.disconnect(websocket=websocket)
        else:
            await manager.disconnect(
                websocket=websocket, code=1007, reason=error_message.value
            )
    else:
        await manager.disconnect(
            websocket=websocket, code=1007, reason="Token query is required"
        )


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
        user, error_message = await validate_azure_token(
            token, check_update_user=check_update_user
        )  
        if user:     
            # initiating agent and message service classes 
            agent_engine_manager = AgentSnowflakeEngineManager()
            message_service = MessageService(
                user=user, chat_id=chat_id, session=maindb_session
            )
            # default connection engine error
            connection_error_message = "Engine is not connected"
            try:
                while True:
                    # checking whether engine is alive 
                    if not agent_engine_manager.is_engine_alive():
                        await manager.send_error_message(
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
                        agent = DataAnalyticAgent(
                            snowflake_engine=agent_engine_manager.engine,
                            chat_id=chat_id, 
                            db_session=maindb_session
                        )
                        # changing connection error message to default in case engine needs to reconnect
                        connection_error_message = "Engine is not connected"

                    # chatting process
                    user_input = await websocket.receive_text()
                    # invoking agent
                    agent_message_id = uuid.uuid4()
                    agent_response, is_agent_response_valid = await agent.invoke(user_query=user_input, message_id=agent_message_id)
                    if is_agent_response_valid:
                        # saving user and agent responses
                        message_service.create_user_message(
                            message_text=user_input
                        )
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
                await manager.disconnect(websocket)

        else:
            await manager.disconnect(
                websocket=websocket, code=1007, reason=error_message.value
            )
    else:
        await manager.disconnect(
            websocket=websocket, code=1007, reason="Token query is required"
        )
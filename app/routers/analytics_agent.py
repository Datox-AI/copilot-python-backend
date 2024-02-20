import uuid, time
import asyncio
from typing import Annotated
from uuid import UUID

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from json.decoder import JSONDecodeError
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


async def listen_for_stop_signal(websocket: WebSocket, stop_event):
    """
    Listen for the "stop" signal from the websocket.
    If received, set the stop_event to stop the main loop.
    """
    try:
        stop_sign = await websocket.receive_json()
        print(stop_sign, " stopppppppp")
        if "command" in stop_sign.keys() and stop_sign["command"] == "stop":
            stop_event.set()
    except Exception as e:
        print(f"Error listening for stop signal: {e}")


@router.websocket("/test")
async def test_ws(
    websocket: WebSocket
):
    await websocket.accept()
    stop_event = asyncio.Event()

    async def receive_messages():
        while not stop_event.is_set():
            data = await websocket.receive_text()
            # Process the data based on its type
            if data == "stop":
                print("stopeeddd")
                stop_event.set()
                print(stop_event.is_set(), " us set")
                break
            else:
                # Handle other messages, e.g., user input
                await websocket.send_text("received22")
                time.sleep(10)
    await receive_messages()


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
                    try:
                        snowflake_token_data = await websocket.receive_json()
                        snowflake_token = snowflake_token_data["oauth_token"]
                    except JSONDecodeError:
                        await manager.disconnect(websocket=websocket, code=1007, reason="You need to send json object")
                        break
                    except KeyError:
                        await manager.disconnect(
                            websocket=websocket, code=1007, reason="'oauth_token' key not found in json object"
                        )
                        break
                    print(type(snowflake_token_data), snowflake_token_data, " ------ received snowflake data")
                    is_valid, error_message = agent_engine_manager.create_engine(
                        snowflake_token=snowflake_token, chat_obj=chat_obj
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
                try:
                    user_input_data = await websocket.receive_json()
                    user_input = user_input_data["user_input"]
                    print(user_input_data, " received")
                except JSONDecodeError:
                    await manager.disconnect(websocket=websocket, code=1007, reason="You need to send json object")
                    break
                except KeyError:
                    await manager.disconnect(
                        websocket=websocket, code=1007, reason="'user_input' key not found in json object"
                    )
                    break

                try:
                    stop_event = asyncio.Event()
                    # Start the background task to listen for the stop signal
                    stop_listener_task = asyncio.create_task(listen_for_stop_signal(websocket, stop_event))
                    # invokeing agent 
                    agent_message_id = uuid.uuid4()
                    agent_run_coroutine = agent.invoke_async(user_query=user_input, message_id=agent_message_id)
                    agent_run_task = asyncio.create_task(agent_run_coroutine)
                    done, pending = await asyncio.wait(
                        {agent_run_task, stop_listener_task}, 
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    if stop_event.is_set():
                        print("Stop signal received or stop listener task completed, canceling agent task...")
                        agent_run_task.cancel()
                        try:
                            # Attempt to gather the agent_run_task to catch the cancellation
                            await agent_run_task
                        except asyncio.CancelledError:
                            await manager.send_stop_notification(websocket=websocket)
                            print("Agent task was cancelled.")                        
                    else:
                        agent_response, is_valid = await agent_run_task
                        if is_valid:
                            # saving user and agent responses
                            message_service.create_user_message(message_text=user_input)
                            message_service.create_agent_response(
                                message_id=agent_message_id,
                                agent_final_output=agent_response["output"],
                                sql_query=agent_response["sql_query"],
                                stored_file_id=agent_response["stored_file_id"],
                                follow_up_questions=agent_response["followup_questions"],
                            )
                            await manager.send_agent_response(response=agent_response, websocket=websocket, chat_id=chat_id)
                        else:
                            await manager.send_error_message(message="Agent failed!", websocket=websocket)
                finally:
                    # Cancel the stop_listener_task if it's still running
                    stop_listener_task.cancel()
                    try:
                        # Wait for the task cancellation to complete
                        await stop_listener_task
                    except asyncio.CancelledError:
                        pass

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
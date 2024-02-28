import uuid, io
import asyncio
from typing import Annotated
from uuid import UUID
import urllib 

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import create_engine

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
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
from app.shared.auth.azure_scheme_for_socket import validate_azure_token
from app.enums.error_enums import SnowflakeTokenErrorEnum
from app.models.maindb.chat import Chat


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


class TokenManager:
    def __init__(self, azure_token, snowflake_token, check_update_user, chat_obj):
        self.azure_token = azure_token 
        self.snowflake_token = snowflake_token
        self.check_update_user = check_update_user
        self.chat_obj = chat_obj
        self.engine = None
    
    def set_values(self, snowflake_token, azure_token):
        self.azure_token = azure_token
        self.snowflake_token = snowflake_token
        
    async def check_tokens(self, snowflake_token=None, azure_token=None):

        if snowflake_token:
            self.snowflake_token = snowflake_token
        if azure_token:
            self.azure_token = azure_token
            
        azure_token_is_valid = False
        azure_token_error_message = ""
        snowflake_token_is_valid = False
        snowflake_token_error_message = ""
        if self.snowflake_token is not None and self.azure_token is not None:
            #checking azure token
            validated_user, azure_token_error_message = await validate_azure_token(
                access_token=self.azure_token, check_update_user=self.check_update_user
            )
            if validated_user:
                print("azure token is valid")
                azure_token_is_valid = True
                # TODO checking chat object 
            else:
                print("azure token is not valid")
            # validating snowflake token
            if self.engine:
                print("have engine")
                
                try:
                    # This is a simple way to check if the connection is alive
                    with self.engine.connect():
                        print("trying connecting")
                        return True
                except SQLAlchemyError:
                    snowflake_token_is_valid = False 
                    snowflake_token_error_message = "Snowflake token is expired"
            else:
                print("createing engine")
                snowflake_token_is_valid, snowflake_token_error_message = self.create_engine()
        else:
            snowflake_token_error_message = "Engine is not connected"
            
        if not snowflake_token_is_valid:
            return snowflake_token_is_valid, snowflake_token_error_message
        elif not azure_token_is_valid:
            return azure_token_is_valid, azure_token_error_message 
     
        return True, ""
                
    def create_engine(self):
        chat_snowflake_data_obj = self.chat_obj.snowflake_data

        snowflake_connection_url = "snowflake://{}/{}/{}?warehouse={}&authenticator=oauth&token={}".format(
            chat_snowflake_data_obj.snowflake_account,
            chat_snowflake_data_obj.database_name,
            chat_snowflake_data_obj.schema,
            chat_snowflake_data_obj.warehouse,
            urllib.parse.quote(self.snowflake_token),
        )
        engine = create_engine(snowflake_connection_url)
        try:
            con = engine.connect()
            con.close()
            self.engine = engine
            return True, ""

        except SQLAlchemyError as e:
            if "Invalid OAuth access token" in str(e.orig):
                error_message = SnowflakeTokenErrorEnum.invalid.value
            elif "OAuth access token expired" in str(e.orig):
                error_message = SnowflakeTokenErrorEnum.expired.value
            else:
                error_message = str(e.orig)
            return False, error_message
    
    

@router.websocket("/ws_new/{chat_id}")
async def agent_endpoint(
    chat_id: UUID,
    websocket: WebSocket,
    check_update_user: Annotated[CheckUpdateUser, Depends()],
    maindb_session: Annotated[Session, Depends(create_maindb_session)],
):
    await manager.connect(websocket=websocket)
    chat_obj = maindb_session.query(Chat).filter(Chat.id == chat_id).first()
    print(chat_obj)
    token_manager = TokenManager(
        azure_token=None,
        snowflake_token=None,
        check_update_user=check_update_user,
        chat_obj=chat_obj
    )
    while True:
        are_tokens_valid, error_message = await token_manager.check_tokens()
        if not are_tokens_valid: 
            await manager.send_error_message(websocket=websocket, message=error_message)    
            result = await manager.receive_token_values(websocket=websocket)
            if result == 'disconnected':
                break
            are_tokens_valid, error_message = await token_manager.check_tokens(snowflake_token=result["snowflake_token"], azure_token=result["azure_token"])
            print(are_tokens_valid, error_message)
            if not are_tokens_valid:
                await manager.send_error_message(message=error_message, websocket=websocket)
                result = await manager.receive_token_values(websocket=websocket)
                if result == 'disconnected':
                    break
                    
                token_manager.set_values(snowflake_token=result["snowflake_token"], azure_token=result["azure_token"])
                continue

            else:
                await manager.send_connection_success_message(websocket=websocket)
                
        received = await websocket.receive_json()
        await websocket.send_text(str(received))
            
    

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
    if is_valid:
        # getting the validated user from validator
        user = validator.validated_user
        chat_obj = validator.chat_obj
        # initiating services
        agent_engine_manager = AgentSnowflakeEngineManager()
        message_service = AnalyticsAgentMessageCreateService(user=user, chat_id=chat_id, session=maindb_session)
        # default connection engine error
        first_message_notification = "Send the azure and snowflake tokens"
        connection_error_message = "Engine is not connected"
        # connection_error_message = "Snowflake token is expired"
        # azure_token_invalid_message = "Azure token is invalid"
        # azure_token_invalid_message = "Azure token is expired"

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
                        print(e, "   agent init error")
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
                    # saving user's message
                    message_service.create_user_message(message_text=user_input)
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
                        {agent_run_task, stop_listener_task}, return_when=asyncio.FIRST_COMPLETED
                    )
                    if stop_event.is_set():
                        print("Stop signal received or stop listener task completed, canceling agent task...")
                        agent_run_task.cancel()
                        try:
                            # Attempt to gather the agent_run_task to catch the cancellation
                            await agent_run_task
                        except asyncio.CancelledError:
                            message_service.create_cancelled_agent_response(message_id=agent_message_id)
                            await manager.send_stop_notification(websocket=websocket, chat_id=chat_id)
                            print("Agent task was cancelled.")
                    else:
                        agent_response, is_valid = await agent_run_task
                        if is_valid:
                            # saving agent's responses
                            message_service.create_agent_response(
                                message_id=agent_message_id, agent_response=agent_response
                            )
                            await manager.send_agent_response(
                                response=agent_response, websocket=websocket, chat_id=chat_id
                            )
                        else:
                            message_service.create_failed_agent_response(
                                message_id=agent_message_id, text=agent_response["error"]
                            )
                            await manager.send_error_message(message=agent_response["error"], websocket=websocket)

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
    return file_service.get_csv_data(request.stored_file_id)


@router.post("/{chat_id}/download_stored_data")
async def download_stored_data(
    chat_id: UUID, request: FileDownloadRequest, file_service: Annotated[AnalyticsAgentFileService, Depends()]
):
    file_data, media_type = file_service.download_file(request.stored_file_id)
    file = io.BytesIO(file_data.readall())
    return StreamingResponse(file, media_type=media_type)

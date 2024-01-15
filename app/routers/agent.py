from fastapi import (
    Cookie,
    Depends,
    APIRouter,
    Query,
    WebSocket,
    WebSocketException,
    WebSocketDisconnect,
    status
    )
from app.schemas.agent.agent_request import AgentRequest
from app.mysocket.connection import ConnectionManager
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
import urllib
from app.infrastructure.agent.agent_service import DataAnalyticAgent, AgentSnowflakeEngineManager
from typing import Annotated

load_dotenv()

router = APIRouter(prefix="/agent")
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket=websocket)
    agent_engine_manager = AgentSnowflakeEngineManager()
    #default connection engine error
    connection_error_message = "Engine is not alive"

    try:
        while True:
            if not agent_engine_manager.is_engine_alive():
                await manager.send_connection_error_message(
                    message=connection_error_message,
                    websocket=websocket
                )
                # await websocket.send_json({"status": connection_error_message})
                snowflake_data = await websocket.receive_json()
                is_valid, error_message = agent_engine_manager.create_engine(snowflake_data)
                if not is_valid:
                    connection_error_message = f"Failed to establish database connection: {error_message}"
                    continue
                # notifying front end about connection is succesful
                await manager.send_connection_success_message(websocket=websocket)                
                # Initialize the agent only if it's not already initialized or if the engine was recreated
                agent = DataAnalyticAgent(snowflake_engine=agent_engine_manager.engine)
                # changing connection error message to default in case engine needs to reconnect
                connection_error_message = "Engine is not alive"

            # chatting with user
            user_input = await websocket.receive_text()
            response = await agent.invoke(user_query=user_input)
            await manager.send_agent_response(response=response, websocket=websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


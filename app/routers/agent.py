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
from app.socket.connection import ConnectionManager
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
import urllib
from app.infrastructure.agent.agent_service import DataAnalyticAgent
from typing import Annotated

load_dotenv()

router = APIRouter(prefix="/agent")
manager = ConnectionManager()

# testing webs 
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("wss://127.0.0.1:7202/agent/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

@router.get("/")
async def get():
    return HTMLResponse(html)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket=websocket)
    # getting the first json data
    snowflake_data = await websocket.receive_json()    
    connection_url = f"snowflake://{snowflake_data['account']}/{snowflake_data['database']}/{snowflake_data['schema']}?warehouse={snowflake_data['warehouse']}&authenticator=oauth&token={urllib.parse.quote(snowflake_data['oauth_token'])}"
    # initiating an agent
    agent = DataAnalyticAgent(sf_connection_url=connection_url)
    await websocket.send_json(
        {
            "message": "Agent is ready!"
        }
    )
    try:
        while True:
            user_input = await websocket.receive_text()

            response = await agent.invoke(user_query=user_input)
            print(response, " respoe")
            await websocket.send_text(f"Message text was: {user_input}")
            await websocket.send_json(
                {
                    "output": response["output"], 
                    "followup_questions": response["followup_questions"]
                }
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# @router.post("/", status_code=status.HTTP_201_CREATED)
# async def create_chat(request: CreateChatRequest, create_chat_service: Annotated[CreateChat, Depends()]):
#     if request is None:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
#     return await create_chat_service.invoke(request)
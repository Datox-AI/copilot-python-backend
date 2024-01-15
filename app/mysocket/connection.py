from fastapi import WebSocket
from typing import List, Dict


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    
    async def send_connection_error_message(self, message: str, websocket: WebSocket):
        await websocket.send_json(
            {
                "status": "error",
                "message": message
            }
        )
    async def send_connection_success_message(self, websocket: WebSocket):
        await websocket.send_json(
            {
                "status": "success",
                "message": "Engine is connected succesfully"
            }
        )

    async def send_agent_response(self, response: Dict, websocket: WebSocket):
                
        await websocket.send_json(
            {
                "output": response["output"], 
                "followup_questions": response["followup_questions"]
            }
        )
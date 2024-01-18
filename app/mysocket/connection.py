import json
from fastapi import WebSocket
from typing import List, Dict

from app.schemas.message import MessageResponse


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(
        self, websocket: WebSocket, code: int = 1000, reason: str = None
    ):
        try:
            await websocket.close(code=code, reason=reason)
        except Exception as e:
            print(f"closing socket raised an error: {e}")
            pass
        finally:
            self.active_connections.remove(websocket)


    async def send_error_message(self, message: str, websocket: WebSocket):
        await websocket.send_json({"status": "error", "message": message})

    async def send_connection_success_message(self, websocket: WebSocket):
        await websocket.send_json(
            {"status": "success", "message": "Engine is connected succesfully"}
        )

    async def send_agent_response(
        self, response: MessageResponse, websocket: WebSocket
    ):
        await websocket.send_json(
            {
                "output": response["output"],
                "followup_questions": response["followup_questions"],
                "stored_file_id": response["stored_file_id"],
                "sql_query": response["sql_query"]
            }
        )

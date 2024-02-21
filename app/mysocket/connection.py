import json
from typing import Dict, List
from uuid import UUID
from fastapi import WebSocket

from app.schemas.message import AnalyticAgentMessageResponse


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(
        self,
        websocket: WebSocket,
        closed: bool = False,
        code: int = 1000,
        reason: str = None,
    ):
        print(f"closing....   reason: {reason}")
        if not closed:
            try:
                await websocket.close(code=code, reason=reason)
            except Exception as e:
                print(f"closing socket raised an error: {e}")
                pass
        self.active_connections.remove(websocket)

    async def send_error_message(self, message: str, websocket: WebSocket):
        await websocket.send_json({"status": "error", "message": message})

    async def send_connection_success_message(self, websocket: WebSocket):
        await websocket.send_json({"status": "success", "message": "Engine is connected succesfully"})

    async def send_stop_notification(self, websocket: WebSocket, chat_id: UUID):
        await websocket.send_json(
            {
                "status": "success",
                "chat_id": chat_id.hex,
                "message": "Agent is stopped",
            }
        )

    async def send_agent_response(self, websocket: WebSocket, response: dict, chat_id: UUID):
        # changing f-questions with choices if there are choices because front end requested like this
        if response["choices"]:
            response["followup_questions"] = response["choices"]
        await websocket.send_json(
            {
                "chat_id": chat_id.hex,
                "output": response["output"],
                "followup_questions": response["followup_questions"],
                "stored_file_id": response["stored_file_id"],
                "sql_query": response["sql_query"],
            }
        )

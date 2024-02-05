from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.schemas.message import CreateMessageRequest, UpdateMessageRequest
from app.services.messages import RAGAgentMessageResponse
from app.infrastructure.rag_agent.agent_service import RAGAgent

router = APIRouter(prefix="/api/rag_agent", tags=["RAG agent"])




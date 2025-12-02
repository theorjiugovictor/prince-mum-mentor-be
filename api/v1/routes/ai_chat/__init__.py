"""
AI Chat module initialization.
This file aggregates all AI chat-related routes and includes them in the main AI chat router.
"""

from fastapi import APIRouter

from .chat import router as ai_chat_router
from .websocket import router as websocket_router


router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])

router.include_router(ai_chat_router)

router.include_router(websocket_router, prefix="/chat")

__all__ = ["router"]

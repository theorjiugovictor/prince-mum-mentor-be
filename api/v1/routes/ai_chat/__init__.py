from .get_user_convos import router
from fastapi import APIRouter
from .get_user_convos import router as get_convos_router
from .send_message import router as send_message_router
from .create_session import router as create_session_router
from .user_conversations import router as list_convos_router
from .delete_chat import router as delete_chat_router
from .websocket import router as websocket_router  # ADD THIS LINE

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])

# Combine all AI chat routers
router.include_router(get_convos_router)
router.include_router(send_message_router)
router.include_router(create_session_router)
router.include_router(list_convos_router)
router.include_router(delete_chat_router)
router.include_router(websocket_router, prefix="/chat")

__all__ = ["router"]

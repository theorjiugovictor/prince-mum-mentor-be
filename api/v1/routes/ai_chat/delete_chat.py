from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
import uuid

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.utils.responses import success_response, fail_response
from api.v1.models.user.user import User
from api.v1.services.chat.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["AI Chat"])

@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a specific chat conversation.
    """
    try:
        result = ChatService.delete_conversation(
            session=db,
            conversation_id=conversation_id,
            user_id=current_user.id
        )

        if result == "not_found":
            logger.warning(f"User {current_user.id} attempted to delete non-existent chat {conversation_id}")
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Conversation not found"
            )

        if result == "forbidden":
            # Return 404 instead of 403 for security
            logger.warning(f"User {current_user.id} attempted to delete not-owned chat {conversation_id}")
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Conversation not found"
            )

        # deleted
        logger.info(f"Chat conversation {conversation_id} deleted successfully by user {current_user.id}")
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Conversation deleted"
        )

    except Exception as e:
        logger.error(f"Error deleting chat {conversation_id}: {str(e)}")
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred."
        )
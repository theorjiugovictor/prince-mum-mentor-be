from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.models.chat_session import ChatSession
from api.utils.responses import success_response
from api.utils.logger import logger
from api.v1.schemas.chat import ConversationTitleUpdate
from api.v1.services.chat.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["AI Chat"])

@router.get("/", status_code=status.HTTP_200_OK)
def list_user_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Conversations per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all chat session tiles of the current user with pagination.
    Only session info (title, created_at) is returned.
    """
    try:
        logger.info(f"Listing chat session tiles | user_id={current_user.id} | page={page} | per_page={per_page}")

        # Fetch all user sessions
        all_sessions = ChatSession.fetch_all(db, user_id=current_user.id)
        total_count = len(all_sessions)

        
        start = (page - 1) * per_page
        end = start + per_page
        paginated_sessions = all_sessions[start:end]

        
        data = [
            {
                "id": str(session.id),
                "user_id": str(session.user_id),
                "title": session.title,
                "created_at": session.created_at.isoformat()
            }
            for session in paginated_sessions
        ]

        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

        response = {
            "conversations": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "next": page + 1 if page < total_pages else None,
                "prev": page - 1 if page > 1 else None
            }
        }

        return success_response(
            status_code=status.HTTP_200_OK,
            message="User conversation tiles retrieved successfully",
            data=response
        )

    except Exception as e:
        logger.error(f"Error listing chat session tiles | user_id={current_user.id} | error={str(e)}")
        raise


@router.patch("/{conversation_id}/title")
def update_chat_title(
        conversation_id: str,
        payload: ConversationTitleUpdate,
        session: Session = Depends(get_db),
        current_user=Depends(get_current_user),
):
    updated, error = ChatService.update_title(
        session=session,
        conversation_id=conversation_id,
        user_id=current_user.id,
        new_title=payload.title,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Chat session title updated successfully.",
        data=updated,
    )
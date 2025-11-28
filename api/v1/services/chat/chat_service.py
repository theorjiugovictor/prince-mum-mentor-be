from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from api.v1.models.chat_session import ChatSession
import uuid

class ChatService:
    @staticmethod
    def delete_conversation(session: Session, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Deletes a chat session only if it exists AND belongs to the user.
        Returns one of: 'deleted', 'not_found', 'forbidden'.
        """
        # Try to locate the session by id without scoping to user first
        chat_session = ChatSession.fetch_one(session, id=conversation_id)

        if not chat_session:
            return "not_found"

        # If session exists but does not belong to requester
        if str(chat_session.user_id) != str(user_id):
            return "forbidden"

        chat_session.delete(session)
        return "deleted"


    @staticmethod
    def update_title(session: Session, conversation_id: str, user_id: str, new_title: str):
        try:
            # 1. Locate the chat session using model helper
            chat_session = ChatSession.fetch_one(
                session,
                id=conversation_id,
                user_id=user_id
            )

            if not chat_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found."
                )

            # 2. Update title
            chat_session.title = new_title
            session.commit()
            session.refresh(chat_session)

            # 3. Return standardized payload
            return {
                "id": str(chat_session.id),
                "title": chat_session.title,
            }

        except HTTPException:
            raise

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while updating the chat title."
            )
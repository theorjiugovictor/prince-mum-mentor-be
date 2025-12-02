"""
This module aggregates all AI chat-related endpoints into a single router.
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.db.database import get_db, SessionLocal
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.utils.responses import success_response, fail_response
from api.v1.models.user.user import User
from api.v1.models.chat_session import ChatSession
from api.v1.schemas.chat import ConversationTitleUpdate
from api.v1.schemas.ai_chat import SendMessageRequest
from api.v1.services.chat.chat_service import ChatService
from api.v1.services.chat_messaging_service import ChatMessagingService
from api.v1.services.get_user_convos import ConversationService

router = APIRouter(prefix="/chats", tags=["AI Chat"])


@router.get("/", status_code=status.HTTP_200_OK)
def list_user_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Conversations per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all chat session tiles of the current user with pagination.
    Only session info (title, created_at) is returned.
    """
    try:
        logger.info(
            "Listing chat session tiles | user_id=%s | page=%s | per_page=%s",
            current_user.id,
            page,
            per_page,
        )

        # Fetch all user sessions
        query = db.query(ChatSession).filter(ChatSession.user_id == current_user.id)
        total_count = query.count()

        paginated_sessions = query.order_by(ChatSession.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        data = [
            {
                "id": str(session.id),
                "user_id": str(session.user_id),
                "title": session.title,
                "created_at": session.created_at.isoformat(),
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
                "prev": page - 1 if page > 1 else None,
            },
        }

        return success_response(
            status_code=status.HTTP_200_OK,
            message="User conversation tiles retrieved successfully",
            data=response,
        )

    except Exception as e:
        logger.error(
            "Error listing chat session tiles | user_id=%s | error=%s",
            current_user.id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving user conversations.",
        ) from e


@router.patch("/{conversation_id}/title")
def update_chat_title(
    conversation_id: str,
    payload: ConversationTitleUpdate,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Updates the title of a specific chat conversation.

    Args:
        conversation_id: The ID of the conversation to update.
        payload: The request body containing the new title.
        session: The database session.
        current_user: The authenticated user.

    Returns:
        A success response with the updated chat session details.
    """
    updated, _ = ChatService.update_title(
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


@router.post("/{session_id}/message")
async def send_message(
    session_id: uuid.UUID,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to AI and stream the response via Server-Sent Events (SSE)

    Flow:
    1. Verify session ownership
    2. Save user message to DB
    3. Generate title if first message (returned in 'start' event)
    4. Check if summarization needed (>50 messages)
    5. Stream AI response
    6. Save AI response after stream completes

    SSE Event Types:
    - start: Initial event with message_id and title (title only present for first message)
    - chunk: AI response content chunks
    - done: Stream completion with AI message_id
    - error: Error occurred during streaming

    Args:
        session_id: UUID of the chat session
        request: SendMessageRequest with message content
        db: Database session
        current_user: Authenticated user

    Returns:
        StreamingResponse with Server-Sent Events
        First message returns: {"type": "start", "message_id": "...", "title": "Generated Title"}
        Subsequent messages: {"type": "start", "message_id": "..."}
    """
    try:
        logger.info("POST /chats/%s/message | user_id=%s", session_id, current_user.id)

        messaging_service = ChatMessagingService(db)

        # Step 1: Verify session ownership
        session = messaging_service.get_session(session_id, current_user.id)

        # Step 2: Save user message immediately
        user_message = messaging_service.save_user_message(session_id, request.message)
        user_message_id = user_message.id

        # Step 3: Check message count for title generation
        message_count = messaging_service.get_message_count(session_id)

        generated_title = None
        if message_count == 1:  # First message in conversation
            logger.info(
                "First message - generating title synchronously | session_id=%s",
                session_id,
            )
            try:
                generated_title = await messaging_service.generate_title_background(
                    session_id, request.message
                )
                logger.info(
                    "Title generated: %s | session_id=%s",
                    generated_title,
                    session_id,
                )
            except ValueError as e:
                logger.error(
                    "Error generating title | session_id=%s | error=%s",
                    session_id,
                    str(e),
                )
                # Continue even if title generation fails

        # Step 4: Generate summary if needed (>50 messages)
        if message_count > ChatMessagingService.MESSAGE_SUMMARY_THRESHOLD:
            logger.info(
                "Message count exceeds threshold - generating summary | session_id=%s",
                session_id,
            )
            # Run synchronously to ensure summary is available for context
            await messaging_service.generate_summary_if_needed(session)

        # Get user message content for context
        user_message_content = request.message
        current_user_id = current_user.id

        # Step 5-6: Stream AI response
        async def event_generator():
            """Generate Server-Sent Events with AI response chunks"""
            accumulated_response = []

            # Create a new database session for the async generator
            stream_db = SessionLocal()

            try:
                # Send initial event with title (if first message)
                start_event = {"type": "start", "message_id": str(user_message_id)}
                if generated_title:
                    start_event["title"] = generated_title
                yield f"data: {json.dumps(start_event)}\n\n"

                # Get fresh session object for streaming
                stream_service = ChatMessagingService(stream_db)
                session_for_stream = stream_service.get_session(
                    session_id, current_user_id
                )

                # Stream AI response chunks
                async for chunk in stream_service.stream_ai_response(
                    session_for_stream, user_message_content
                ):
                    accumulated_response.append(chunk)
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                # Save complete AI response to database
                full_response = "".join(accumulated_response)
                ai_message = stream_service.save_ai_message(session_id, full_response)

                # Send completion event
                yield f"data: {json.dumps({'type': 'done', 'message_id': str(ai_message.id)})}\n\n"

                logger.info(
                    "Message stream completed | session_id=%s | response_length=%s",
                    session_id,
                    len(full_response),
                )

            except ValueError as e:
                logger.error(
                    "Error during streaming | session_id=%s | error=%s",
                    session_id,
                    str(e),
                )
                yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred'})}\n\n"
            finally:
                # Clean up the database session
                stream_db.close()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except ValueError as e:
        logger.error(
            "Error in send_message | session_id=%s | error=%s", session_id, str(e)
        )
        raise


@router.get("/{convo_id}")
def get_user_convos(
    convo_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Messages per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a conversation (chat session) by ID with all its messages (paginated).

    Args:
        convo_id: UUID of the conversation
        page: Page number for pagination (default: 1)
        per_page: Number of messages per page (default: 20, max: 100)
        db: Database session
        current_user: Authenticated user

    Returns:
        Conversation details with paginated messages

    Raises:
        404: Conversation not found
        403: User does not have access to this conversation
    """
    try:
        logger.info(
            "GET /chats/%s | user_id=%s | page=%s | per_page=%s",
            convo_id,
            current_user.id,
            page,
            per_page,
        )

        conversation_service = ConversationService(db)

        session = conversation_service.get_conversation_by_id(convo_id, current_user.id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        messages, total_count = conversation_service.get_conversation_messages(
            convo_id, page, per_page
        )

        messages_data = [
            {
                "id": str(message.id),
                "sender": message.sender,
                "message": message.message,
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ]

        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

        # Prepare response data
        response_data = {
            "conversation": {
                "id": str(session.id),
                "user_id": str(session.user_id),
                "title": session.title,
                "created_at": (
                    session.created_at.isoformat() if session.created_at else None
                ),
            },
            "messages": messages_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "next": page + 1 if page < total_pages else None,
                "prev": page - 1 if page > 1 else None,
            },
        }

        logger.info(
            "Conversation retrieved successfully | convo_id=%s | messages_count=%s",
            convo_id,
            len(messages_data),
        )

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Conversation retrieved successfully",
            data=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error retrieving conversation | convo_id=%s | error=%s", convo_id, str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the conversation",
        ) from e


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a specific chat conversation.
    """
    try:
        result = ChatService.delete_conversation(
            session=db, conversation_id=conversation_id, user_id=current_user.id
        )

        if result == "not_found":
            logger.warning(
                "User %s attempted to delete non-existent chat %s",
                current_user.id,
                conversation_id,
            )
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND, message="Conversation not found"
            )

        if result == "forbidden":
            # Return 404 instead of 403 for security
            logger.warning(
                "User %s attempted to delete not-owned chat %s",
                current_user.id,
                conversation_id,
            )
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND, message="Conversation not found"
            )

        # deleted
        logger.info(
            "Chat conversation %s deleted successfully by user %s",
            conversation_id,
            current_user.id,
        )
        return success_response(
            status_code=status.HTTP_200_OK, message="Conversation deleted"
        )

    except HTTPException:
        raise  # Re-raise HTTPException if it's already one
    except Exception as e:
        logger.error("Error deleting chat %s: %s", conversation_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        ) from e


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_chat_session(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Create a new chat session for the current user

    The title will be automatically generated when the user sends their first message.

    Args:
        db: Database session
        current_user: Authenticated user

    Returns:
        Created chat session details (title will be None initially)
    """
    try:
        logger.info("Creating new chat session | user_id=%s", current_user.id)

        # Create new session without title (will be generated on first message)
        session = ChatSession(
            user_id=current_user.id, title=None, created_at=datetime.now(timezone.utc)
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info(
            "Chat session created | session_id=%s | user_id=%s",
            session.id,
            current_user.id,
        )

        # Prepare response
        session_data = {
            "id": str(session.id),
            "user_id": str(session.user_id),
            "title": session.title,
            "created_at": session.created_at.isoformat(),
        }

        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Chat session created successfully",
            data=session_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error creating chat session | user_id=%s | error=%s",
            current_user.id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the chat session",
        ) from e

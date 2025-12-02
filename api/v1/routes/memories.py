"""
This module contains the API endpoints for managing memories.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.utils.responses import fail_response, success_response
from api.v1.models.user.user import User
from api.v1.schemas.album_memories import AlbumMemoriesResponse
from api.v1.schemas.memories import MemoryCreateRequest, MemoryResponse
from api.v1.services.album_memories import AlbumMemoryService
from api.v1.services.memories_service import MemoriesService

router = APIRouter(prefix="/memories", tags=["Memories"])


@router.get(
    "/albums/{album_id}/memories",
    description="get a list of memories in an album",
    response_model=AlbumMemoriesResponse,
)
def get_album_memories(  
    album_id: UUID,  
    db: Session = Depends(get_db),  
    current_user: User = Depends(get_current_user),  
):
    """
    Get all memories for a specific album.
    """
    try:
        album = AlbumMemoryService.get_album_by_id(db, album_id)

        if not album:
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"album with album id: {album_id} not found",
            )

        memories = AlbumMemoryService.get_memories_by_album_id(db, album_id)

        return success_response(
            status_code=status.HTTP_200_OK,
            message="album memories retrieved successfully",
            data=AlbumMemoriesResponse(
                id=album.id,
                name=album.name,
                memories=[MemoryResponse.from_orm(m) for m in memories],
            ).model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "exception occurred in get album memories endpoint: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal server error",
        ) from e


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a memory",
    response_description="Memory created successfully",
)
def create_memory_endpoint(
    payload: MemoryCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new memory for the authenticated user."""

    service = MemoriesService(db)
    memory, error = service.create_memory(payload=payload, current_user=current_user)

    if error:
        status_code, message = error
        logger.warning(
            "Create memory failed | user_id=%s | status=%s | message=%s",
            current_user.id,
            status_code,
            message,
        )
        return fail_response(status_code=status_code, message=message)

    response_data = MemoryResponse.model_validate(memory)

    logger.info(
        "Create memory succeeded | memory_id=%s | user_id=%s",
        response_data.id,
        current_user.id,
    )

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Memory created successfully",
        data=response_data.model_dump(),
    )


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a memory",
    response_description="Memory deleted successfully",
)
def delete_memory_endpoint(
    memory_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one of the authenticated user's memories by ID."""

    service = MemoriesService(db)
    deleted, error = service.delete_memory(memory_id=memory_id, user_id=current_user.id)

    if error:
        status_code, message = error
        logger.warning(
            "Delete memory failed | memory_id=%s | user_id=%s | status=%s | message=%s",
            memory_id,
            current_user.id,
            status_code,
            message,
        )
        return fail_response(status_code=status_code, message=message)

    if not deleted:
        logger.error(
            "Delete memory returned false without error | memory_id=%s | user_id=%s",
            memory_id,
            current_user.id,
        )
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Could not delete memory",
        )

    logger.info(
        "Delete memory succeeded | memory_id=%s | user_id=%s",
        memory_id,
        current_user.id,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Memory deleted successfully",
        data={"memory_id": str(memory_id)},
    )

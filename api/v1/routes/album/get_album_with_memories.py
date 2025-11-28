from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.utils.responses import success_response, fail_response
from api.v1.models.user.user import User
from api.v1.services.album_service import AlbumService
from api.v1.schemas.album import AlbumWithMemoriesResponse, AlbumListItem, RenameAlbumRequest
from typing import List

album_router = APIRouter(prefix="/albums", tags=["Albums"])


@album_router.get("/{album_id}", response_model=AlbumWithMemoriesResponse)
def get_album_with_memories(
    album_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get an album with all its memories and photos by album ID for the authenticated user.

    Args:
        album_id: The UUID of the album to retrieve
        db: Database session
        current_user: Authenticated user

    Returns:
        AlbumWithMemoriesResponse: Album data with associated memories and photos

    Raises:
        HTTPException: If album not found or doesn't belong to user
    """
    logger.info(f"Getting album {album_id} with memories for user {current_user.id}")

    try:
        album_service = AlbumService(db)
        album = album_service.get_album_with_memories_by_id(album_id, current_user.id)

        if not album:
            logger.warning(f"Album {album_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Album not found"
            )

        logger.info(f"Successfully retrieved album {album_id} with {len(album.memories)} memories")
        return album

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving album {album_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the album"
        )

@album_router.get("/", response_model=List[AlbumListItem])
def list_albums(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List albums for the authenticated user, including a thumbnail image (first or last uploaded).
    """
    logger.info(f"Listing albums for user {current_user.id}")

    try:
        album_service = AlbumService(db)
        albums = album_service.list_albums_with_thumbnail(current_user.id, prefer_last=True)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="User albums",
            data=albums
        )

    except Exception as e:
        logger.error(f"Error listing albums for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing albums"
        )

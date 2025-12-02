"""
This module contains the API endpoints for managing albums.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.utils.responses import success_response, fail_response
from api.v1.models.user.user import User
from api.v1.schemas.albums import AlbumCreate
from api.v1.schemas.album import AlbumWithMemoriesResponse, AlbumListItem
from api.v1.services.album_service import (
    AlbumService,
    create_album as create_album_service,
    delete_album as delete_album_service,
)

router = APIRouter(prefix="/album", tags=["Albums"])


@router.get("/{album_id}", response_model=AlbumWithMemoriesResponse)
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
    logger.info("Getting album %s with memories for user %s", album_id, current_user.id)

    try:
        album_service = AlbumService(db)
        album = album_service.get_album_with_memories_by_id(album_id, current_user.id)

        if not album:
            logger.warning("Album %s not found for user %s", album_id, current_user.id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Album not found"
            )

        logger.info(
            "Successfully retrieved album %s with %s memories",
            album_id,
            len(album.memories),
        )
        return album

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving album %s: %s", album_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the album",
        ) from e


@router.get("/", response_model=List[AlbumListItem])
def list_albums(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List albums for the authenticated user, including a thumbnail image (first or last uploaded).
    """
    logger.info("Listing albums for user %s", current_user.id)

    try:
        album_service = AlbumService(db)
        albums = album_service.list_albums_with_thumbnail(
            current_user.id, prefer_last=True
        )
        return success_response(
            status_code=status.HTTP_200_OK, message="User albums", data=albums
        )

    except Exception as e:
        logger.error("Error listing albums for user %s: %s", current_user.id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing albums",
        ) from e


@router.delete("/{album_id}", status_code=status.HTTP_200_OK)
def delete_album(
    album_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Deletes an album for the authenticated user.
    """
    _, error = delete_album_service(db=db, album_id=album_id, user_id=user.id)

    if error:
        return fail_response(400, error)

    return success_response(status_code=200, message="Album deleted successfully")


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_album(
    payload: AlbumCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Creates a new album for the authenticated user.
    """
    try:
        album = create_album_service(db=db, user_id=user.id, name=payload.name)
        return success_response(
            status_code=201,
            message="Album created successfully",
            data={"album_id": str(album.id), "name": album.name},
        )
    except Exception as e:
        logger.error("Album creation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the album.",
        ) from e

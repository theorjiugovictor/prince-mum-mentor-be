from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid

from api.v1.models.resource.resource_media import ResourceMedia


class ResourceMediaService:
    """Service for handling resource media operations."""

    @staticmethod
    def get_media_by_id(session: Session, media_id: uuid.UUID) -> dict:
        """
        Get a single media file (photo or video) by its ID.
        
        Args:
            session: Database session
            media_id: UUID of the media
            
        Returns:
            Dictionary containing media details
            
        Raises:
            HTTPException: If media not found
        """
        # Query the media
        media = session.query(ResourceMedia).filter(ResourceMedia.id == media_id).first()
        
        if not media:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        # Return media details
        return {
            "id": media.id,
            "resource_id": media.resource_id,
            "url": media.url,
            "media_type": media.media_type
        }

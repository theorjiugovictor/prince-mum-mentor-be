from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.responses import success_response
from api.v1.schemas.resource_media import ResourceMediaResponse
from api.v1.services.resource_media import ResourceMediaService

router = APIRouter(prefix="/resource-media", tags=["Resource Media"])


@router.get("/{media_id}", status_code=status.HTTP_200_OK)
def view_resource_media(
    media_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    View a single media file (photo or video) from a community post.
    
    This endpoint retrieves details of a specific media file associated with
    a community resource post.
    
    **Path Parameters:**
    - media_id (required): UUID of the media file to view
    
    **Authentication:**
    - Requires valid access token
    
    **Returns:**
    - Media details including:
      - id: Media UUID
      - resource_id: UUID of the post this media belongs to
      - url: Direct URL to the media file
      - media_type: Either "photo" or "video"
    
    **Example Response:**
    ```json
    {
      "status": "success",
      "status_code": 200,
      "message": "Media retrieved successfully",
      "data": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "resource_id": "987fcdeb-51a2-43f7-b123-456789abcdef",
        "url": "https://example.com/media/video.mp4",
        "media_type": "video"
      }
    }
    ```
    
    **Error Responses:**
    - 404: Media not found
    - 401: Unauthorized (invalid or missing token)
    """
    media_data = ResourceMediaService.get_media_by_id(session, media_id)
    
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Media retrieved successfully",
        data=media_data
    )

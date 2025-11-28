"""
Route for uploading child profile picture.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.services.child_profile_service import ChildProfileService
from api.v1.services.child_profile_image_upload import save_child_profile_image, delete_child_profile_image
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger
from pathlib import Path


router = APIRouter(prefix="/child-profiles", tags=["Child Profiles"])


UPLOAD_DIR = Path("app/uploads/child_profiles")

@router.post("/{child_id}/upload-picture", status_code=status.HTTP_200_OK)
async def upload_child_profile_picture(
    child_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a profile picture for a child.
    
    This endpoint allows uploading an image file for a child's profile picture.
    The image is stored locally and the URL is saved to the database.
    
    Supported formats: JPEG, PNG, WebP
    Maximum size: 5MB
    """
    logger.info(f"Uploading profile picture for child {child_id} by user {current_user.id}")
    
    try:
        # Get child profile and verify ownership
        child = ChildProfileService.get_child_profile(
            db=db,
            child_id=child_id,
            user_id=current_user.id
        )
        
        if not child:
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Child profile not found",
                context={"child_id": str(child_id)}
            )
        
        # Delete old image if exists
        if child.get("profile_picture_url"):
            delete_child_profile_image(child["profile_picture_url"])
        
        # Upload new image
        image_url = await save_child_profile_image(file)
        
        # Update database
        from api.v1.schemas.child_profile import UpdateChildProfileRequest
        update_request = UpdateChildProfileRequest(profile_picture_url=image_url)
        
        updated_child = ChildProfileService.update_child_profile(
            db=db,
            child_id=child_id,
            user_id=current_user.id,
            request=update_request
        )
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Profile picture uploaded successfully",
            data=updated_child
        )
        
    except Exception as e:
        logger.error(f"Error uploading profile picture for child {child_id}: {e}")
        return fail_response(
            status_code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=getattr(e, "detail", "Failed to upload profile picture"),
            context={"error": str(e)}
        )


@router.get("/avatar/{filename}", status_code=status.HTTP_200_OK)
async def get_child_avatar(filename: str):
    """
    Serve child profile avatar image.
    
    **Public endpoint - no authentication required**
    
    This allows avatars to be displayed without authentication,
    making them usable in <img> tags and shareable.
    """
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar image not found"
        )
    
    # Determine media type based on file extension
    ext = filename.split(".")[-1].lower()
    media_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp"
    }
    media_type = media_types.get(ext, "image/jpeg")
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )
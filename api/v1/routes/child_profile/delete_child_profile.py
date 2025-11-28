"""
Route for deleting a child profile.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.services.child_profile_service import ChildProfileService
from api.v1.services.child_profile_image_upload import delete_child_profile_image
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger


router = APIRouter(prefix="/child-profiles", tags=["Child Profiles"])


@router.delete("/{child_id}", status_code=status.HTTP_200_OK)
def delete_child_profile(
    child_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a child profile.
    
    This is a hard delete operation that also removes the profile picture from storage.
    """
    logger.info(f"Deleting child profile {child_id} for user {current_user.id}")
    
    try:
        # Get child profile first to get image URL
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
        
        # Delete profile picture if exists
        if child.get("profile_picture_url"):
            delete_child_profile_image(child["profile_picture_url"])
            logger.info(f"Deleted profile picture for child {child_id}")
        
        # Delete child profile from database
        success = ChildProfileService.delete_child_profile(
            db=db,
            child_id=child_id,
            user_id=current_user.id
        )
        
        if success:
            return success_response(
                status_code=status.HTTP_200_OK,
                message="Child profile deleted successfully",
                data={"deleted": True, "child_id": str(child_id)}
            )
        else:
            return fail_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to delete child profile",
                context={"child_id": str(child_id)}
            )
        
    except Exception as e:
        logger.error(f"Error deleting child profile {child_id}: {e}")
        return fail_response(
            status_code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=getattr(e, "detail", "Failed to delete child profile"),
            context={"error": str(e)}
        )


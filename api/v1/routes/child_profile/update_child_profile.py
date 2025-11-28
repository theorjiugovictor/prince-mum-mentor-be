"""
Route for updating a child profile.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.schemas.child_profile import UpdateChildProfileRequest
from api.v1.services.child_profile_service import ChildProfileService
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger


router = APIRouter(prefix="/child-profiles", tags=["Child Profiles"])


@router.patch("/{child_id}", status_code=status.HTTP_200_OK)
def update_child_profile(
    child_id: UUID,
    request: UpdateChildProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a child profile.
    
    Only fields provided in the request will be updated (partial update).
    """
    logger.info(f"Updating child profile {child_id} for user {current_user.id}")
    
    try:
        child = ChildProfileService.update_child_profile(
            db=db,
            child_id=child_id,
            user_id=current_user.id,
            request=request
        )
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Child profile updated successfully",
            data=child
        )
        
    except Exception as e:
        logger.error(f"Error updating child profile {child_id}: {e}")
        return fail_response(
            status_code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=getattr(e, "detail", "Failed to update child profile"),
            context={"error": str(e)}
        )

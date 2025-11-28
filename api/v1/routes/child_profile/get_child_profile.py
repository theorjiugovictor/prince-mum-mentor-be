"""
Route for getting a single child profile.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.services.child_profile_service import ChildProfileService
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger


router = APIRouter(prefix="/child-profiles", tags=["Child Profiles"])


@router.get("/{child_id}", status_code=status.HTTP_200_OK)
def get_child_profile(
    child_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single child profile by ID.
    
    Only returns the child profile if it belongs to the current user.
    """
    logger.info(f"Getting child profile {child_id} for user {current_user.id}")
    
    try:
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
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Child profile retrieved successfully",
            data=child
        )
        
    except Exception as e:
        logger.error(f"Error getting child profile {child_id}: {e}")
        return fail_response(
            status_code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=getattr(e, "detail", "Failed to retrieve child profile"),
            context={"error": str(e)}
        )

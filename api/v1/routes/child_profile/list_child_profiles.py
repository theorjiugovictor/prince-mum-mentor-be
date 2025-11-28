"""
Route for listing all child profiles for the current user.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.services.child_profile_service import ChildProfileService
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger


router = APIRouter(prefix="/child-profiles", tags=["Child Profiles"])


@router.get("/", status_code=status.HTTP_200_OK)
def list_child_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all child profiles for the current user.
    
    Returns an empty list if the user has no children.
    """
    logger.info(f"Listing child profiles for user {current_user.id}")
    
    try:
        children = ChildProfileService.get_all_child_profiles(
            db=db,
            user_id=current_user.id
        )
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Child profiles retrieved successfully",
            data={"children": children, "total": len(children)}
        )
        
    except Exception as e:
        logger.error(f"Error listing child profiles for user {current_user.id}: {e}")
        return fail_response(
            status_code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=getattr(e, "detail", "Failed to retrieve child profiles"),
            context={"error": str(e)}
        )

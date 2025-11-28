"""
Route for creating a child profile.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.schemas.child_profile import CreateChildProfileRequest
from api.v1.services.child_profile_service import ChildProfileService
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger


router = APIRouter(prefix="/child-profiles", tags=["Child Profiles"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_child_profile(
    request: CreateChildProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new child profile.
    
    The child profile will be linked to the user's profile setup.
    """
    logger.info(f"Creating child profile for user {current_user.id}")
    
    try:
        child = ChildProfileService.create_child_profile(
            db=db,
            user_id=current_user.id,
            request=request
        )
        
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Child profile created successfully",
            data=child
        )
        
    except Exception as e:
        logger.error(f"Error creating child profile: {e}")
        return fail_response(
            status_code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=getattr(e, "detail", "Failed to create child profile"),
            context={"error": str(e)}
        )

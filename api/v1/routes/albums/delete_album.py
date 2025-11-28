from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from api.db.database import get_db
from api.utils.responses import success_response, fail_response
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.v1.services.album_service import delete_album as delete_album_service
from api.v1.models.user.user import User

router = APIRouter()

@router.delete("/{album_id}", status_code=status.HTTP_200_OK)
def delete_album(
    album_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result, error = delete_album_service(
        db=db,
        album_id=album_id,
        user_id=user.id
    )

    if error:
        return fail_response(400, error)

    return success_response(
        status_code=200,
        message="Album deleted successfully"
    )

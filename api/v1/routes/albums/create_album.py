from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from api.db.database import get_db
from api.utils.responses import success_response, fail_response
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.v1.schemas.albums import AlbumCreate
from api.v1.services.album_service import create_album as create_album_service
from api.v1.models.user.user import User

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_album(
    payload: AlbumCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        album = create_album_service(
            db=db,
            user_id=user.id,
            name=payload.name
        )
        return success_response(
            status_code=201,
            message="Album created successfully",
            data={"album_id": str(album.id), "name": album.name}
        )
    except Exception as e:
        logger.error(f"Album creation failed: {e}", exc_info=True)
        return fail_response(500, "An unexpected error occurred while creating the album")

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.v1.models.user.user import User
from api.v1.services.album_memories import AlbumMemoryService
from api.v1.schemas.album_memories import AlbumMemoriesResponse, MemoryResponse
from api.utils.responses import fail_response, success_response


router = APIRouter(prefix='/albums', tags=['Albums'])

@router.get(
    '/{album_id}/memories',
    description="get a list of memories in an album",
    response_model=AlbumMemoriesResponse
)
def get_album_memories(
        album_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        album = AlbumMemoryService.get_album_by_id(db, album_id)

        if not album:
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"album with album id: {album_id} not found"
            )

        memories = AlbumMemoryService.get_memories_by_album_id(db, album_id)

        return success_response(
            status_code=status.HTTP_200_OK,
            message="album memories retrieved successfully",
            data=AlbumMemoriesResponse(
                id=album.id,
                name=album.name,
                memories=[MemoryResponse.from_orm(m) for m in memories]
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("exception occurred in get album memories endpoint: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal server error"
        )


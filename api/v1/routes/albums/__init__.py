from fastapi import APIRouter
from .create_album import router as create_album_router
from .delete_album import router as delete_album_router

router = APIRouter(prefix="/album", tags=["Albums"])
router.include_router(create_album_router)
router.include_router(delete_album_router)

__all__ = ["router"]

from fastapi import APIRouter, UploadFile, Depends, Request
from sqlalchemy.orm import Session
from api.db.database import get_db
from api.utils.responses import fail_response
from api.v1.schemas.image_schema import PhotoResponse
from api.v1.services.image import ImageService
from api.v1.models.photos import Photos
from fastapi.responses import FileResponse
import os
from api.utils.deps import get_current_user, security
from uuid import UUID
from api.v1.schemas.memories import MemoryCreateRequest
from api.v1.services.memories_service import MemoriesService
from api.utils.responses import success_response


UPLOAD_DIR = "app/uploads"
router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/upload", response_model=PhotoResponse, status_code = 201)
async def upload_photo(request: Request, file: UploadFile, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Upload a photo, compress if needed, store in uploads folder and url in database,
    and return the saved photo info.
    """
    response = await ImageService.save_and_compress_image(request, file, db)
    return response


@router.post("/{photo_id}/link-to-album", status_code=201)
async def link_image_to_album(
    photo_id: UUID,
    album_id: UUID,
    note: str = "",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Link an uploaded image to an album by creating a memory.
    """
    # Verify photo exists and belongs to user
    photo = db.query(Photos).filter(Photos.id == photo_id).first()
    if not photo:
        return fail_response(message="Photo not found", status_code=404)
    
    # Create memory using existing service
    memory_service = MemoriesService(db)
    memory_payload = MemoryCreateRequest(
        album_id=album_id,
        photo=photo_id,
        note=note
    )
    
    memory, error = memory_service.create_memory(
        payload=memory_payload, 
        current_user=current_user
    )
    
    if error:
        status_code, message = error
        return fail_response(status_code=status_code, message=message)
    
    return success_response(
        message="Image successfully added to album",
        data={
            "memory_id": memory.id,
            "album_id": memory.album_id,
            "photo_id": memory.photo,
            "note": memory.note
        },
        status_code=201
    )


@router.delete("/delete/{photo_id}")
async def delete_photo(photo_id: str, db: Session = Depends(get_db), status_code=204, current_user=Depends(get_current_user)):
    """
    Delete a photo by ID, remove it from storage and database.
    """
    # Delete file using the service
    file_delete_response = ImageService.delete_image( db, photo_id)
    return file_delete_response


@router.get("/{photo_id}", response_model=PhotoResponse, status_code=200)
async def get_photo(photo_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a photo by ID.
    """
    response = ImageService.get_photo_by_id(db, photo_id)
    return response

@router.get("/download/{photo_id}.jpg", status_code=200)
async def download_photo(photo_id: str, db: Session = Depends(get_db)):
    # fetch photo record
    photo = db.query(Photos).filter(Photos.id == photo_id).first()
    if not photo:
        return fail_response(message="Photo not found", status_code=404)
    
    # extract filename from stored URL
    filename = photo.image_url.split("/")[-1]
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        return fail_response(message="File not found on server", status_code=404)

    # return file for download
    return FileResponse(
        path=file_path, 
        filename=filename, 
        media_type="image/jpeg"
    )


@router.delete("/delete", status_code=204)
async def delete_all_photos(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    response = ImageService.delete_all_photos(db)
    return response


@router.get("/", response_model=list[PhotoResponse])
async def get_all_photos(db: Session = Depends(get_db)):
    """
    Get all photos metadata.
    """
    response = ImageService.get_all_photos(db)
    return response
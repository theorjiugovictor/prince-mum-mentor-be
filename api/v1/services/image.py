from api.utils.responses import fail_response, success_response, JSONResponse
import os
import uuid
from fastapi import Request, UploadFile
from sqlalchemy.orm import Session
from api.v1.models.photos import Photos
from PIL import Image

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_SIZE_MB = 2  # compress images larger than 2MB


class ImageService:

    @staticmethod
    async def save_and_compress_image(request: Request, file: UploadFile, db: Session) -> JSONResponse:
        # Validate file type
        if not file.content_type.startswith(("image/jpg", "image/png", "image/jpeg", "image/webp")):
            return fail_response(message="Unsupported file type", status_code=400)

        file_bytes = await file.read()
        size_mb = len(file_bytes) / (1024 * 1024)
        unq = uuid.uuid4()
        filename = f"{unq}.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Save original file
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        if size_mb > MAX_SIZE_MB * 20:
            return fail_response(message="File too large", status_code=500)
        # Compress if larger than threshold
        if size_mb > MAX_SIZE_MB:
            try:
                img = Image.open(file_path)
                img = img.convert("RGB")
                img.save(file_path, "JPEG", optimize=True, quality=70)
            except Exception:
                return fail_response(message="Image compression failed", status_code=500)

        # Build full URL (no double slash)
        base_url = str(request.base_url).rstrip("/")
        image_url = f"{base_url}/api/v1/images/download/{filename}"

        # Save to database
        photo = Photos(image_url=image_url, id=unq)
        db.add(photo)
        db.commit()
        db.refresh(photo)

        return success_response(
            message="Photo uploaded successfully",
            data={"id": photo.id, "image_url": photo.image_url},
            status_code=201
        )

    @staticmethod
    def delete_image(db: Session, photo_id: str) -> JSONResponse | None:
        photo = db.query(Photos).filter(Photos.id == photo_id).first()
        if not photo:
            return fail_response(
                message=f"Image not found {photo_id}",
                status_code=500
            )
        print("\n\n\n", photo, "\n\n\n")
        # Delete db record
        db.delete(photo)
        db.commit()

        image_url= photo.image_url
            # Extract filename from URL
        filename =  image_url.split("/")[-1]
        if not photo:
            return fail_response(message="Photo not found", status_code=404)

        file_path = os.path.join(UPLOAD_DIR, filename)

        # Delete file if exists
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            return fail_response(message="File not found", status_code=404)

        # Delete db record
        db.delete(photo)
        db.commit()

        return success_response(message="File deleted successfully", status_code=204)
    @staticmethod
    def delete_all_photos(db: Session) -> JSONResponse | None:
        photos = db.query(Photos).all()
        if not photos:
            return fail_response(message="No photos to delete", status_code=404)
        
        for photo in photos:
            # Delete file from storage
            image_url= photo.image_url
            filename =  image_url.split("/")[-1]
            file_path = os.path.join(UPLOAD_DIR, filename)

            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete db record
            db.delete(photo)
        db.commit()
        return success_response(message="All photos deleted successfully", status_code=204)
        
    @staticmethod
    def get_photo_by_id(db: Session, photo_id: str) -> JSONResponse | None:
        photo = db.query(Photos).filter(Photos.id == photo_id).first()
        if not photo:
            return fail_response(message="Photo not found", status_code=404)
        return success_response(
            message="Photo retrieved successfully",
            data={"id": photo.id, "image_url": photo.image_url},
            status_code=200
        ) if photo else fail_response(message="Photo not found", status_code=404)
    
    @staticmethod
    def get_all_photos(db: Session) -> JSONResponse:
        photos = db.query(Photos).all()
        photo_list = [{"id": photo.id, "image_url": photo.image_url} for photo in photos]
        return success_response(
            message="Photos retrieved successfully",
            data={"photos": photo_list},
            status_code=200
        )

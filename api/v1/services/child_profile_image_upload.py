"""
Utility functions for handling child profile image uploads.
This is a temporary local storage solution that can be easily migrated to cloud storage later.
"""

import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status

from api.utils.logger import logger


UPLOAD_DIR = Path("app/uploads/child_profiles")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
BASE_URL = "/files/child_profiles"


def ensure_upload_directory_exists():
    """Ensure the upload directory exists."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_image_file(file: UploadFile) -> None:
    """
    Validate uploaded image file.
    
    Args:
        file: The uploaded file
        
    Raises:
        HTTPException: If file is invalid
    """
    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check content type
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: {file.content_type}"
        )


async def save_child_profile_image(file: UploadFile) -> str:
    """
    Save child profile image to local storage.
    
    Args:
        file: The uploaded image file
        
    Returns:
        URL path to the saved image
        
    Raises:
        HTTPException: If upload fails
    """
    try:
        # Validate file
        validate_image_file(file)
        
        # Ensure directory exists
        ensure_upload_directory_exists()
        
        # Generate unique filename
        file_ext = file.filename.split(".")[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Read file content
        contents = await file.read()
        
        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)}MB"
            )
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)
        

        image_url = f"{BASE_URL}/{unique_filename}"
        
        logger.info(f"Image saved successfully: {image_url}")
        
        return image_url
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )


def delete_child_profile_image(image_url: Optional[str]) -> bool:
    """
    Delete child profile image from local storage.
    
    Args:
        image_url: URL path to the image
        
    Returns:
        True if deleted successfully or image doesn't exist, False on error
    """
    if not image_url:
        return True
    
    try:
        # Extract filename from URL
        # URL format: /files/child_profiles/filename.jpg
        if BASE_URL in image_url:
            filename = image_url.split("/")[-1]
            file_path = UPLOAD_DIR / filename
            
            # Delete file if it exists
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Image deleted successfully: {image_url}")
                return True
            else:
                logger.warning(f"Image file not found: {image_url}")
                return True  # File doesn't exist, so consider it deleted
        else:
            logger.warning(f"Invalid image URL format: {image_url}")
            return True  # Not our local file, skip deletion
            
    except Exception as e:
        logger.error(f"Error deleting image {image_url}: {e}")
        return False


def get_absolute_image_url(base_url: str, image_url: Optional[str]) -> Optional[str]:
    """
    Convert relative image URL to absolute URL.
    
    Args:
        base_url: Base URL of the API (e.g., https://api.example.com)
        image_url: Relative image URL (e.g., /files/child_profiles/uuid.jpg)
        
    Returns:
        Absolute URL or None
    """
    if not image_url:
        return None
    
    if image_url.startswith("http"):
        return image_url
    
    return f"{base_url.rstrip('/')}{image_url}"
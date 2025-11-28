from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional


class PhotoResponse(BaseModel):
    """Schema for photo data in memory response"""
    id: UUID
    image_url: str

    class Config:
        from_attributes = True


class MemoryResponse(BaseModel):
    """Schema for memory response"""
    id: UUID
    album_id: UUID
    photo_data: PhotoResponse
    note: str
    saved_on: datetime

    class Config:
        from_attributes = True


class AlbumWithMemoriesResponse(BaseModel):
    """Schema for album with memories response"""
    id: UUID
    name: str
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    memories: List[MemoryResponse] = []

    class Config:
        from_attributes = True


class AlbumListItem(BaseModel):
    """Schema for album listing with thumbnail"""
    id: UUID
    name: str
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    last_image: Optional[str] = None

    class Config:
        from_attributes = True


class RenameAlbumRequest(BaseModel):
    """Schema for renaming an album"""
    name: str

    class Config:
        schema_extra = {
            "example": {"name": "My Updated Album Name"}
        }
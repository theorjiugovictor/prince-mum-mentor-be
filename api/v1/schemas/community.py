from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

class PostPhotoDTO(BaseModel):
    id: uuid.UUID
    url: str

    class Config:
        from_attributes = True

class PostCommentUserDTO(BaseModel):
    """User info for comment responses"""
    id: uuid.UUID
    full_name: str

    class Config:
        from_attributes = True

class PostCommentDTO(BaseModel):
    """Comment info for post responses"""
    id: uuid.UUID
    post_id: uuid.UUID
    user_id: uuid.UUID
    user: PostCommentUserDTO
    comment: str
    created_at: datetime
    parent_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True

class PostUserDTO(BaseModel):
    """User info for post responses"""
    id: uuid.UUID
    full_name: str

    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user: PostUserDTO
    title: str
    content: str
    created_at: datetime
    views: int
    photos: List[PostPhotoDTO] = []
    comments: List[PostCommentDTO] = []
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False
    
    class Config:
        from_attributes = True

class PostResponseWrapper(BaseModel):
    status: str
    message: str
    data: PostResponse

class LikeToggleResponse(BaseModel):
    """Response after toggling a like"""
    is_liked: bool
    likes_count: int

class LikeResponseWrapper(BaseModel):
    status: str
    message: str
    data: LikeToggleResponse
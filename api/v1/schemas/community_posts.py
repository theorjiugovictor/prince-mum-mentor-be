from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class PostCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(...)
    photo_ids: Optional[List[UUID]] = Field(default=None, description="List of uploaded photo IDs to attach to post")


class PostUserResponse(BaseModel):
    """user info for post responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    full_name: str

class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    user: PostUserResponse
    title: str
    content: str
    views: int
    created_at: datetime
    photos: List["PostPhotoResponse"] = []
    likes_count: int = 0
    comments_count: int = 0


class PostPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    post_id: UUID
    url: str


class PostCommentUserResponse(BaseModel):
    """User info for comment responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    full_name: str


class PostCommentResponse(BaseModel):
    """Comment info for post responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    post_id: UUID
    user_id: UUID
    user: PostCommentUserResponse
    comment: str
    created_at: datetime
    parent_id: Optional[UUID] = None


class CommentCreateRequest(BaseModel):
    comment: str


# schemas for paginated response
class PostsPagination(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class AllPostsResponse(BaseModel):
    posts: List[PostResponse]
    pagination: PostsPagination


PostResponse.model_rebuild()
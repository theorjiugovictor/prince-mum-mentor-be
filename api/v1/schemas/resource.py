from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

class ResourceMediaDTO(BaseModel):
    id: uuid.UUID
    url: str
    media_type: str

    class Config:
        from_attributes = True

class ResourceCategoryDTO(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True

class ResourceResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    
    created_at: datetime 
    category: ResourceCategoryDTO
    media: List[ResourceMediaDTO]
    
    class Config:
        from_attributes = True

class PaginatedResourceResponse(BaseModel):
    status: str
    message: str
    data: List[ResourceResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class CreateResourceBookmark(BaseModel):
    resource_id: uuid.UUID

from pydantic import BaseModel
from uuid import UUID

# --- Category Schemas ---
class CategoryCreate(BaseModel):
    name: str

# --- Resource Schemas ---
class ResourceCreate(BaseModel):
    title: str
    content: str
    category_id: UUID

class ResourceUpdate(BaseModel):
    title: str
    content: str
    category_id: UUID | None = None
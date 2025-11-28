from pydantic import BaseModel
import uuid


class ResourceMediaResponse(BaseModel):
    """Schema for resource media response."""
    id: uuid.UUID
    resource_id: uuid.UUID
    url: str
    media_type: str

    class Config:
        from_attributes = True

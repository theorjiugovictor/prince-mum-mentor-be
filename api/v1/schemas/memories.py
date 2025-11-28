from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class MemoryCreateRequest(BaseModel):
    """Payload for creating a new memory."""

    album_id: UUID = Field(..., description="Album identifier that groups the memory")
    photo: UUID = Field(..., description="Photo to associate with the memory")
    note: str = Field(..., max_length=250, description="Note describing the memory")
    saved_on: datetime | None = Field(
        None,
        description="Optional timestamp describing when the memory was saved. If omitted, server default is used.",
    )


class MemoryResponse(BaseModel):
    """Response model for a memory record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    album_id: UUID
    photo: UUID
    note: str
    saved_on: datetime

from typing import List
from pydantic import BaseModel
import uuid

class MemoryResponse(BaseModel):
    id: uuid.UUID
    photo: uuid.UUID
    note: str

    class Config:
        from_attributes = True

class AlbumMemoriesResponse(BaseModel):
    id: uuid.UUID
    name: str
    memories: List[MemoryResponse]

    class Config:
        from_attributes = True

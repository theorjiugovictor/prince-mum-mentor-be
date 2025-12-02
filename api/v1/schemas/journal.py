from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class JournalCreateRequest(BaseModel):
    """Schema for creating a journal entry"""
    title: str = Field(..., min_length=1, description="Title of the journal entry")
    date: datetime = Field(..., description="Date of the journal entry")
    category: Optional[str] = Field(None, description="Category of the journal entry")
    mood: Optional[str] = Field(None, description="Mood of the journal entry")
    photos: List[str] = Field(default=[], description="List of photo URLs")
    thoughts: str = Field(..., min_length=1, description="Content of the journal entry")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "My Day",
                "date": "2025-11-27T10:00:00Z",
                "category": "Food",
                "mood": "Happy",
                "photos": ["https://example.com/photo1.jpg"],
                "thoughts": "Today was a great day! I ate Bole and Fish."
            }
        }
    }

class JournalCreateResponse(BaseModel):
    """Schema for journal creation response"""
    journal_entry_id: uuid.UUID
    title: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "journal_entry_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "My Day"
            }
        }
    }

class JournalEdit(BaseModel):
    title: Optional[str] = None
    entry_date: Optional[datetime] = None
    category: Optional[str] = None
    mood: Optional[str] = None
    photo_urls: Optional[List[str]] = None
    content: Optional[str] = Field(None, alias="thoughts")

class JournalData(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    mood: Optional[str]
    entry_date: datetime
    created_at: datetime
    updated_at: Optional[datetime]
    category_id: Optional[uuid.UUID] = None
    class Config:
        from_attributes = True

class JournalResponse(BaseModel):
    status: str
    message: str
    data: JournalData

class GetAllJournalsQuery(BaseModel):
    limit: int = Field(10, ge=1, le=100, description="Number of entries to return")
    offset: int = Field(0, ge=0, description="Number of entries to skip")
    sort_by: str = Field("entry_date", description="Field to sort by (entry_date or created_at)")
    order: str = Field("desc", description="Sort order (asc or desc)")
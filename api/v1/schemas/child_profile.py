"""
Pydantic schemas for child profile operations.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateChildProfileRequest(BaseModel):
    """Schema for creating a new child profile."""
    profile_setup_id: UUID = Field(..., description="ID of the parent's profile setup")
    full_name: str = Field(..., min_length=1, max_length=120, description="Child's full name")
    date_of_birth: Optional[date] = Field(None, description="Child's date of birth")
    due_date: Optional[date] = Field(None, description="Expected due date if pregnant")
    gender: Optional[str] = Field(None, max_length=50, description="Child's gender")
    birth_order: Optional[int] = Field(None, ge=1, description="Birth order among siblings")
    profile_picture_url: Optional[str] = Field(None, description="URL to child's profile picture")


class UpdateChildProfileRequest(BaseModel):
    """Schema for updating a child profile. All fields are optional for partial updates."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=120, description="Child's full name")
    date_of_birth: Optional[date] = Field(None, description="Child's date of birth")
    due_date: Optional[date] = Field(None, description="Expected due date if pregnant")
    gender: Optional[str] = Field(None, max_length=50, description="Child's gender")
    birth_order: Optional[int] = Field(None, ge=1, description="Birth order among siblings")
    profile_picture_url: Optional[str] = Field(None, description="URL to child's profile picture")


class ChildProfileResponse(BaseModel):
    """Schema for child profile response."""
    id: UUID
    profile_setup_id: UUID
    full_name: str
    date_of_birth: Optional[date] = None
    due_date: Optional[date] = None
    gender: Optional[str] = None
    birth_order: Optional[int] = None
    profile_picture_url: Optional[str] = None
    age: Optional[int] = None  # Calculated field
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True

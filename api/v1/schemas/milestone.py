from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Union
from datetime import datetime
import uuid

# Define the 4 predefined categories for mothers
MotherCategoryType = Literal["Body Recovery", "Mental Wellness", "Routine Builder", "Self Care"]

# Define the 4 predefined categories for children
ChildCategoryType = Literal["Development", "Health and Nutrition", "Activities and Play", "Growth Check"]

# Combined category type
CategoryType = Union[MotherCategoryType, ChildCategoryType]

class MilestoneBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: CategoryType
    child_id: Optional[uuid.UUID] = None

class MilestoneCreate(MilestoneBase):
    pass

class MilestoneUpdate(BaseModel):
    """Schema for updating milestone fields (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[CategoryType] = None

class MilestoneToggle(BaseModel):
    completed: bool
    child_id: Optional[uuid.UUID] = None

class MilestoneResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    owner_type: str
    name: str
    description: Optional[str]
    status: str
    category: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
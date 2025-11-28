# api/v1/models/milestones.py

import uuid
from typing import List
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from api.db.base_model import BaseModel
import enum

class MotherCategory(str, enum.Enum):
    """Predefined milestone categories for mothers."""
    BODY_RECOVERY = "Body Recovery"
    MENTAL_WELLNESS = "Mental Wellness"
    ROUTINE_BUILDER = "Routine Builder"
    SELF_CARE = "Self Care"

class ChildCategory(str, enum.Enum):
    """Predefined milestone categories for children."""
    DEVELOPMENT = "Development"
    HEALTH_NUTRITION = "Health and Nutrition"
    ACTIVITIES_PLAY = "Activities and Play"
    GROWTH_CHECK = "Growth Check"

class Milestone(BaseModel):
    __tablename__ = "milestones"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    owner_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "mother" | "child"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | completed
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Category as simple string field
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
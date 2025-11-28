# api/v1/models/milestone_category.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel


class MilestoneCategory(BaseModel):
    __tablename__ = "milestone_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    owner_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "mother" | "child" | "system"

    description: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    milestones = relationship("Milestone", back_populates="category")

# api/v1/models/categories.py

import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from api.db.base_model import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    owner_type: Mapped[str] = mapped_column(
        String(20), nullable=False  # "mother" | "child"
    )

    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
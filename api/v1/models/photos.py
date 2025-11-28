import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base_model import BaseModel

class Photos(BaseModel):
    __tablename__ = "photos"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    image_url: Mapped[str] = mapped_column(String(200))

    # Relationships
    # If a Photo is deleted, cascade delete associated Memory records
    memories = relationship("Memory", back_populates="photo_data", cascade="all, delete")
    
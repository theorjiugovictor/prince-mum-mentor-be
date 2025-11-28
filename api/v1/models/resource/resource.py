import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.resource.resource_category import ResourceCategory
    from api.v1.models.resource.resource_media import ResourceMedia
    from api.v1.models.resource.resource_likes import ResourceLike
    from api.v1.models.resource.resource_comment import ResourceComment
    from api.v1.models.resource.saved_for_later import SavedForLater

class Resource(BaseModel):
    __tablename__ = "resource"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resource_categories.id"), nullable=False)

    # Relationships
    category: Mapped["ResourceCategory"] = relationship("ResourceCategory", back_populates="resources")
    
    # allows for: resource.media, resource.likes, resource.comments
    media: Mapped[list["ResourceMedia"]] = relationship("ResourceMedia", back_populates="resource", cascade="all, delete-orphan")
    likes: Mapped[list["ResourceLike"]] = relationship("ResourceLike", back_populates="resource", cascade="all, delete-orphan")
    comments: Mapped[list["ResourceComment"]] = relationship("ResourceComment", back_populates="resource", cascade="all, delete-orphan")
    saved: Mapped[list["SavedForLater"]] = relationship("SavedForLater", back_populates="resource", cascade="all, delete-orphan")
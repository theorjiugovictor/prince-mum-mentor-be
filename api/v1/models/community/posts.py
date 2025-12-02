import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.community.post_photos import PostPhoto
    from api.v1.models.community.post_likes import PostLike
    from api.v1.models.community.post_comments import PostComment
    from api.v1.models.user.user import User

class Post(BaseModel):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    views: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="posts") 
    photos: Mapped[list["PostPhoto"]] = relationship("PostPhoto", back_populates="post", cascade="all, delete-orphan")
    likes: Mapped[list["PostLike"]] = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    comments: Mapped[list["PostComment"]] = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")
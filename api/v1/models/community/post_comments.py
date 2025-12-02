import uuid
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.community.posts import Post
    from api.v1.models.user.user import User

class PostComment(BaseModel):
    __tablename__ = "post_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"), nullable=False)
    
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("post_comments.id"), nullable=True)
    
    comment: Mapped[str] = mapped_column(String, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    post: Mapped["Post"] = relationship("Post", back_populates="comments")
    user: Mapped["User"] = relationship("User")
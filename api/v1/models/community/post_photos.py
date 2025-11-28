import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.community.posts import Post

class PostPhoto(BaseModel):
    __tablename__ = "post_photos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)

    post: Mapped["Post"] = relationship("Post", back_populates="photos")
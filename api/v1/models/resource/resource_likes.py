import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.resource.resource import Resource

class ResourceLike(BaseModel):
    __tablename__ = "resource_likes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resource.id"), nullable=False)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    resource: Mapped["Resource"] = relationship("Resource", back_populates="likes")
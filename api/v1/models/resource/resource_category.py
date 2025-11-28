import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.resource.resource import Resource

class ResourceCategory(BaseModel):
    __tablename__ = "resource_categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    resources: Mapped[list["Resource"]] = relationship("Resource", back_populates="category")
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.journal.journal import Journal

class JournalCategory(BaseModel):
    __tablename__ = "journal_categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    journal: Mapped[list["Journal"]] = relationship("Journal", back_populates="category")
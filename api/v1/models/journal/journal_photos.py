import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.journal.journal import Journal

class JournalPhoto(BaseModel):
    __tablename__ = "journal_photos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    journal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("journal.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)

    journal: Mapped["Journal"] = relationship("Journal", back_populates="photos")
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from api.db.base_model import BaseModel

if TYPE_CHECKING:
    from api.v1.models.journal.journal_photos import JournalPhoto
    from api.v1.models.journal.journal_category import JournalCategory

class Journal(BaseModel):
    __tablename__ = "journal"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    mood: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    views: Mapped[int] = mapped_column(Integer, default=0)
    
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_categories.id"), nullable=True)

    photos: Mapped[list["JournalPhoto"]] = relationship("JournalPhoto", back_populates="journal", cascade="all, delete-orphan")
    category: Mapped[Optional["JournalCategory"]] = relationship("JournalCategory", back_populates="journal")
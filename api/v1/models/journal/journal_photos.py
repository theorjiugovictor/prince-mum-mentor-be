from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.db.base_model import BaseModel
import uuid

class JournalPhoto(BaseModel):
    __tablename__ = "journal_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_id = Column(UUID(as_uuid=True), ForeignKey("journal.id"), nullable=False)
    url = Column(String, nullable=False)

    journal = relationship("Journal", back_populates="photos")
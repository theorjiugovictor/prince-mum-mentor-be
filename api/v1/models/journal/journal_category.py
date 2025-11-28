from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.db.base_model import BaseModel
import uuid

class JournalCategory(BaseModel):
    __tablename__ = "journal_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    
    journals = relationship("Journal", back_populates="category")
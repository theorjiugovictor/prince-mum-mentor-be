from sqlalchemy import Column, String, UUID
from api.db.base_model import BaseModel
import uuid

class JournalComment(BaseModel):
    __tablename__ = "journal_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    parent_id = Column(UUID(as_uuid=True), nullable=True)
    comment = Column(String, nullable=False)
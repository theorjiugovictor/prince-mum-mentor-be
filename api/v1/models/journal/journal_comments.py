import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from api.db.base_model import BaseModel

class JournalComment(BaseModel):
    __tablename__ = "journal_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    journal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    
    comment: Mapped[str] = mapped_column(String, nullable=False)
import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from api.db.base_model import BaseModel

class JournalLike(BaseModel):
    __tablename__ = "journal_likes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    journal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    comment_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
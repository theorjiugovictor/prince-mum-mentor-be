from sqlalchemy import Column, String, UUID
from api.db.base_model import BaseModel
import uuid

class ResourceMedia(BaseModel):
    __tablename__ = "resource_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), nullable=False)
    url = Column(String, nullable=False)
    media_type = Column(String(10), nullable=False)  # "photo" or "video"
from pydantic import BaseModel, ConfigDict
import uuid

class PhotoResponse(BaseModel):
    id: uuid.UUID
    image_url: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "image_url": "https://example.com/images/photo.jpg"}}
    )
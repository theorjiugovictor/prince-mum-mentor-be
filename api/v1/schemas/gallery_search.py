from pydantic import BaseModel
from datetime import datetime
from typing import Any


class SearchResultItem(BaseModel):
    type: str
    id: str
    name: str | None = None
    note: str | None = None
    album_id: str | None = None
    album_name: str | None = None
    photo_url: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    results: list[SearchResultItem]

    model_config = {"from_attributes": True}

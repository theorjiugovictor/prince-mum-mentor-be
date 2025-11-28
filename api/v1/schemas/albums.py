from pydantic import BaseModel

class AlbumCreate(BaseModel):
    name: str

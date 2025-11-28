from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.v1.models.albums import Album
from api.v1.models.memories import Memory
from api.v1.models.photos import Photos


def _escape_like(query: str) -> str:
    return query.replace("%", "\\%").replace("_", "\\_")


def search_gallery(db: Session, user_id, query: str, limit: int = 25, offset: int = 0) -> List[Dict[str, Any]]:
    """Search albums by name and memories by note for a given user.

    Returns a combined list of results with a simple unified shape.
    """
    query = (query or "").strip()
    if not query:
        return []

    escaped = f"%{_escape_like(query)}%"

    results: List[Dict[str, Any]] = []

    # Search albums owned by the user
    albums_stmt = (
        select(Album)
        .where(Album.user_id == user_id, Album.name.ilike(escaped, escape='\\'))
        .limit(limit)
        .offset(offset)
    )

    albums = db.scalars(albums_stmt).all()
    for a in albums:
        results.append(
            {
                "type": "album",
                "id": str(a.id),
                "name": a.name,
                "created_at": a.created_at,
            }
        )

    # Search memories where notes match and belong to user's albums
    memories_stmt = (
        select(Memory, Album, Photos)
        .join(Album, Memory.album_id == Album.id)
        .outerjoin(Photos, Memory.photo == Photos.id)
        .where(Album.user_id == user_id, Memory.note.ilike(escaped, escape='\\'))
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(memories_stmt).all()
    for memory, album, photo in rows:
        results.append(
            {
                "type": "memory",
                "id": str(memory.id),
                "note": memory.note,
                "album_id": str(album.id),
                "album_name": album.name,
                "photo_url": getattr(photo, "image_url", None),
                "created_at": memory.saved_on,
            }
        )

    return results

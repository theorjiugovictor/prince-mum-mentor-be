from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from api.v1.models.albums import Album
from api.v1.models.memories import Memory
from api.v1.models.photos import Photos
import uuid


class AlbumService:
    """Service for album operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_album_with_memories_by_id(self, album_id: uuid.UUID, user_id: uuid.UUID) -> Album | None:
        """
        Get an album with all its memories and photos by album ID for a specific user.

        Args:
            album_id: The UUID of the album
            user_id: The UUID of the user who owns the album

        Returns:
            Album object with loaded memories and photos, or None if not found
        """
        # Query album with joined memories and photos
        stmt = (
            select(Album)
            .options(
                joinedload(Album.memories).joinedload(Memory.photo_data)
            )
            .where(Album.id == album_id, Album.user_id == user_id)
        )

        result = self.db.execute(stmt)
        album = result.unique().scalar_one_or_none()

        return album

    def list_albums_with_thumbnail(self, user_id: uuid.UUID, prefer_last: bool = True) -> list:
        """
        List albums for a user and include a thumbnail image (first or last uploaded photo).

        Args:
            user_id: UUID of the owner
            prefer_last: if True use the most recent memory, otherwise use the oldest

        Returns:
            List of dicts with album and `last_image` (image_url or None)
        """
        albums = self.db.query(Album).filter(Album.user_id == user_id).order_by(Album.created_at.desc()).all()

        results = []
        for album in albums:
            # get the memory entry (first or last)
            order = Memory.saved_on.desc() if prefer_last else Memory.saved_on.asc()
            last_memory = (
                self.db.query(Memory)
                .filter(Memory.album_id == album.id)
                .order_by(order)
                .limit(1)
                .first()
            )

            last_image = None
            if last_memory and last_memory.photo:
                photo = self.db.query(Photos).filter(Photos.id == last_memory.photo).first()
                if photo:
                    last_image = photo.image_url

            results.append({
                "id": album.id,
                "name": album.name,
                "user_id": album.user_id,
                "created_at": album.created_at,
                "updated_at": album.updated_at,
                "last_image": last_image,
            })

        return results
from sqlalchemy.orm import Session
from uuid import UUID
from api.v1.models.albums import Album
from api.utils.logger import logger

def create_album(db: Session, user_id: UUID, name: str):
    album = Album(
        name=name,
        user_id=user_id
    )
    db.add(album)
    db.commit()
    db.refresh(album)
    logger.info(f"Album created: {album.id} by user {user_id}")
    return album

def delete_album(db: Session, album_id: UUID, user_id: UUID):
    album = db.query(Album).filter(
        Album.id == album_id,
        Album.user_id == user_id
    ).first()

    if not album:
        return None, "Album not found"

    db.delete(album)
    db.commit()
    logger.info(f"Album deleted: {album_id} by user {user_id}")
    return True, None

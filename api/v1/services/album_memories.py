from sqlalchemy.orm import Session
import uuid

from api.v1.models.albums import Album
from api.v1.models.memories import Memory
from api.utils.logger import logger


class AlbumMemoryService:
    """Service class to handle album and memory operations"""

    @staticmethod
    def get_album_by_id(db: Session, album_id: uuid.UUID):
        """
        Fetch an album by its ID

        Args:
            db: Database session
            album_id: Album UUID

        Returns:
            Album object or None if not found
        """
        try:
            album = db.query(Album).filter(Album.id == album_id).first()
            if not album:
                logger.warning("Album not found: %s", album_id)
            return album
        except Exception as e:
            logger.error("Error fetching album %s: %s", album_id, str(e), exc_info=True)
            return None

    @staticmethod
    def get_memories_by_album_id(db: Session, album_id: uuid.UUID):
        """
        Fetch all memories associated with an album

        Args:
            db: Database session
            album_id: Album UUID

        Returns:
            List of Memory objects (empty list if none found)
        """
        try:
            memories = db.query(Memory).filter(Memory.album_id == album_id).all()
            return memories
        except Exception as e:
            logger.error("Error fetching memories for album %s: %s", album_id, str(e), exc_info=True)
            return []
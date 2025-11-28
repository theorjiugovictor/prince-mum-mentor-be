"""Service layer for memory operations."""

from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from api.utils.logger import logger
from api.v1.models.memories import Memory
from api.v1.models.albums import Album
from api.v1.models.photos import Photos
from api.v1.models.user.user import User
from api.v1.schemas.memories import MemoryCreateRequest


class MemoriesService:
    """Encapsulates create/delete operations for memories."""

    def __init__(self, db: Session):
        self.db = db

    def _album_exists(self, album_id: UUID) -> bool:
        return (
            self.db.query(Album)
            .filter(Album.id == album_id)
            .first()
            is not None
        )

    def _photo_exists(self, photo_id: UUID) -> bool:
        return (
            self.db.query(Photos)
            .filter(Photos.id == photo_id)
            .first()
            is not None
        )

    def create_memory(
        self, *, payload: MemoryCreateRequest, current_user: User
    ) -> Tuple[Optional[Memory], Optional[Tuple[int, str]]]:
        """Create a new memory record."""
        try:
            album = self.db.query(Album).filter_by(id=payload.album_id, user_id=current_user.id).first()
            if not album:
                logger.warning("Album not found or does not belong to user | album_id=%s", payload.album_id)
                return None, (404, "Album not found")

            if not self._photo_exists(payload.photo):
                logger.warning("Photo not found | photo_id=%s", payload.photo)
                return None, (404, "Photo not found")

            existing = (
                self.db.query(Memory)
                .filter(
                    Memory.album_id == payload.album_id,
                    Memory.photo == payload.photo,
                )
                .first()
            )
            if existing:
                logger.info(
                    "Memory already exists | album_id=%s | photo_id=%s",
                    payload.album_id,
                    payload.photo,
                )
                return None, (409, "Memory already exists")

            memory_kwargs = {
                "album_id": payload.album_id,
                "photo": payload.photo,
                "note": payload.note,
            }

            # Only set saved_on when the client provided a value; otherwise allow the DB/model default
            if getattr(payload, "saved_on", None) is not None:
                memory_kwargs["saved_on"] = payload.saved_on

            memory = Memory(**memory_kwargs)

            self.db.add(memory)
            self.db.commit()
            self.db.refresh(memory)

            logger.info("Memory created | memory_id=%s", memory.id)
            return memory, None

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Error creating memory | album_id=%s | photo_id=%s | error=%s",
                payload.album_id,
                payload.photo,
                exc,
            )
            self.db.rollback()
            return None, (500, "Failed to create memory")

    def delete_memory(
        self, *, memory_id: UUID, user_id: UUID
    ) -> Tuple[bool, Optional[Tuple[int, str]]]:
        """Delete a memory by identifier for the given user."""
        try:
            memory = (
                self.db.query(Memory)
                .join(Album, Album.id == Memory.album_id)
                .filter(Memory.id == memory_id, Album.user_id == user_id)
                .first()
            )

            if not memory:
                logger.warning(
                    "Memory not found for deletion | memory_id=%s",
                    memory_id,
                )
                return False, (404, "Memory not found")

            self.db.delete(memory)
            self.db.commit()

            logger.info("Memory deleted | memory_id=%s", memory_id)
            return True, None

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Error deleting memory | memory_id=%s | error=%s",
                memory_id,
                exc,
            )
            self.db.rollback()
            return False, (500, "Failed to delete memory")

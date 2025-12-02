from typing import Optional
import uuid
from sqlalchemy.orm import Session
from api.v1.models.journal.journal import Journal
from api.v1.models.journal.journal_photos import JournalPhoto
from api.v1.models.journal.journal_category import JournalCategory
from api.v1.schemas.journal import JournalCreateRequest, JournalEdit
from api.utils.logger import logger

class JournalService:
    """Service class for journal-related operations"""

    @staticmethod
    def create_journal(
        db: Session, 
        journal_data: JournalCreateRequest, 
        user_id: str
    ) -> Optional[Journal]:
        """
        Create a new journal entry
        
        Args:
            db: Database session
            journal_data: Journal creation data
            user_id: ID of the user creating the journal
            
        Returns:
            Created Journal object or None if failed
        """
        try:
            # Handle Category - create or find existing category
            category_id: Optional[uuid.UUID] = None
            if journal_data.category:
                # Check if category exists
                existing_category = db.query(JournalCategory).filter(JournalCategory.name == journal_data.category).first()
                
                if existing_category:
                    category_id = existing_category.id
                else:
                    new_category = JournalCategory(name=journal_data.category)
                    db.add(new_category)
                    db.flush()
                    category_id = new_category.id

            new_journal = Journal(
                user_id=uuid.UUID(user_id),
                title=journal_data.title,
                content=journal_data.thoughts,
                category_id=category_id,
                mood=journal_data.mood,
                entry_date=journal_data.date
            )
            
            db.add(new_journal)
            db.flush() 
            
            # Save photos if any
            if journal_data.photos:
                for photo_url in journal_data.photos:
                    new_photo = JournalPhoto(
                        journal_id=new_journal.id,
                        url=photo_url
                    )
                    db.add(new_photo)
            
            db.commit()
            db.refresh(new_journal)
            
            logger.info("Journal created successfully for user_id=%s", user_id)
            return new_journal
            
        except Exception as e:
            db.rollback()
            logger.error("Error creating journal for user_id=%s: %s", user_id, str(e), exc_info=True)
            return None

    @staticmethod
    def delete_journal(db: Session, journal_id: uuid.UUID, user_id: uuid.UUID):
        """
        Deletes a journal entry.
        """
        journal = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if journal:
            db.delete(journal)
            db.commit()
            logger.info("Journal entry %s deleted successfully.", journal_id)
            return True
        logger.warning("Journal entry %s not found for user %s.", journal_id, user_id)
        return False

    @staticmethod
    def update_journal(db: Session, journal_id: uuid.UUID, user_id: uuid.UUID, payload: JournalEdit) -> Optional[Journal]:
        """
        Updates a journal entry.
        """
        journal = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
        if journal:
            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(journal, key, value)
            db.commit()
            db.refresh(journal)
            logger.info("Journal entry %s updated successfully.", journal_id)
            return journal
        logger.warning("Journal entry %s not found for user %s.", journal_id, user_id)
        return None

    @staticmethod
    def get_all_journals(
        db: Session,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
        sort_by: str = "entry_date",
        order: str = "desc"
    ) -> dict:
        """
        Get all journal entries for a user with pagination and sorting
        
        Args:
            db: Database session
            user_id: ID of the user
            limit: Number of entries to return
            offset: Number of entries to skip
            sort_by: Field to sort by (entry_date or created_at)
            order: Sort order (asc or desc)
            
        Returns:
            Dictionary with entries list and total count
        """
        try:
            # Get all journals for the user
            all_journals = db.query(Journal).filter(Journal.user_id == uuid.UUID(user_id)).all()
            
            total = len(all_journals)
            
            if sort_by == "created_at":
                all_journals.sort(
                    key=lambda j: j.created_at,
                    reverse=(order.lower() == "desc")
                )
            else:  # sort by entry_date
                all_journals.sort(
                    key=lambda j: j.entry_date,
                    reverse=(order.lower() == "desc")
                )
            
            journals = all_journals[offset:offset + limit]
            
            # Format response
            entries = []
            for journal in journals:
                entry = {
                    "id": str(journal.id),
                    "title": journal.title,
                    "content": journal.content,
                    "mood": journal.mood,
                    "entry_date": journal.entry_date.isoformat() if journal.entry_date else None,
                    "created_at": journal.created_at.isoformat() if journal.created_at else None,
                    "updated_at": journal.updated_at.isoformat() if journal.updated_at else None,
                    "views": journal.views,
                    "category": {
                        "id": str(journal.category.id),
                        "name": journal.category.name
                    } if journal.category else None,
                    "photos": [{"id": str(photo.id), "url": photo.url} for photo in journal.photos]
                }
                entries.append(entry)
            
            logger.info("Retrieved %s journal entries for user_id=%s", len(entries), user_id)
            
            return {
                "entries": entries,
                "total": total
            }
            
        except Exception as e:
            logger.error("Error retrieving journals for user_id=%s: %s", user_id, str(e), exc_info=True)
            raise
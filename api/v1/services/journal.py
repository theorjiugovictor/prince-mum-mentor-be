from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid

from api.v1.models.journal.journal import Journal
from api.v1.models.journal.journal_photos import JournalPhoto
from api.v1.schemas.journal import JournalEdit
from api.utils.logger import logger

class JournalService:
    
    @staticmethod
    def update_journal(session: Session, journal_id: uuid.UUID, user_id: uuid.UUID, payload: JournalEdit):
        logger.info(f"User {user_id} attempting to edit journal {journal_id}")

        journal = Journal.fetch_one(session, id=journal_id, user_id=user_id)

        if not journal:
            logger.warning(f"Journal {journal_id} not found or unauthorized for user {user_id}")
            raise HTTPException(status_code=404, detail="Journal entry not found")

        update_data = payload.model_dump(exclude_unset=True, by_alias=False)
        
        for field in ["title", "content", "mood", "entry_date", "category_id"]:
            if field in update_data and update_data[field] is not None:
                setattr(journal, field, update_data[field])

        if "photo_urls" in update_data and update_data["photo_urls"] is not None:
            session.query(JournalPhoto).filter(JournalPhoto.journal_id == journal.id).delete()
            for url in update_data["photo_urls"]:
                new_photo = JournalPhoto(journal_id=journal.id, url=url)
                session.add(new_photo)

        try:
            updated_journal = journal.update(session)
            
            logger.info(f"Journal {journal_id} successfully updated")
            return updated_journal
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating journal {journal_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred while updating the journal")
    
    @staticmethod
    def delete_journal(session: Session, journal_id: uuid.UUID, user_id: uuid.UUID):
        """
        Delete a journal entry
        
        Args:
            session: Database session
            journal_id: ID of the journal to delete
            user_id: ID of the user requesting deletion
            
        Returns:
            True if deletion successful
            
        Raises:
            HTTPException: If journal not found or user unauthorized
        """
        logger.info(f"User {user_id} attempting to delete journal {journal_id}")
        
        # Find the journal and verify ownership
        journal = session.query(Journal).filter(
            Journal.id == journal_id,
            Journal.user_id == user_id
        ).first()
        
        if not journal:
            logger.warning(f"Journal {journal_id} not found or unauthorized for user {user_id}")
            raise HTTPException(status_code=404, detail="Journal entry not found")
        
        try:
            # Delete the journal (photos will cascade delete automatically)
            session.delete(journal)
            session.commit()
            logger.info(f"Journal {journal_id} successfully deleted")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting journal {journal_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred while deleting the journal")
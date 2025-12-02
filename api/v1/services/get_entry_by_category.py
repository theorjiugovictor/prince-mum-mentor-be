import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select
from api.v1.models.journal import Journal, JournalCategory

def get_entries_by_category(db: Session, category_title: str, user_id: uuid.UUID, limit: int = 10, offset: int = 0):
    """
    Get journal entries by category title for a specific user with pagination.
    
    Args:
        db: Database session
        category_title: Category name to search for (partial match)
        user_id: User ID for security
        limit: Maximum number of results
        offset: Number of results to skip
    
    Returns:
        List of Journal entries
    """
    stmt = select(Journal).join(JournalCategory).where(
        JournalCategory.name.ilike(f"%{category_title}%"),
        Journal.user_id == user_id
    ).order_by(Journal.created_at.desc()).limit(limit).offset(offset)
    
    result = db.execute(stmt)
    return result.scalars().all()

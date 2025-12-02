import uuid
from ..models.resource.saved_for_later import SavedForLater
from sqlalchemy.orm import Session

# The name "SavedForLater" was an egregious oversight in naming conventions.
# It did imply a "Bookmarked Resource" but heniwaysss...

def create_resource_bookmark(db: Session, user_id: uuid.UUID, resource_id: uuid.UUID):
    new_bookmark = SavedForLater(user_id=user_id, resource_id=resource_id)
    db.add(new_bookmark)
    db.commit()
    db.refresh(new_bookmark)
    return new_bookmark
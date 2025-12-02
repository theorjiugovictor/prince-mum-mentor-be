import uuid
from datetime import datetime
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from api.db.base_model import Base
from api.db.database import get_db
from api.v1.models.user.user import User
from api.v1.models.journal.journal import Journal
from api.v1.models.journal.journal_photos import JournalPhoto
from api.v1.dependencies.auth import get_current_user

TEST_DATABASE_URL = "sqlite:///./test_delete_journal.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh database"""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_user(client):
    """Create a test user"""
    db = TestingSessionLocal()
    user = User(full_name="Journal User", email="delete@test.com", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user
    db.close()
    return user


@pytest.fixture(scope="function")
def user_journal(client, test_user):
    """Create a test journal for the user"""
    db = TestingSessionLocal()
    journal = Journal(
        user_id=test_user.id,
        title="Test Journal",
        content="This is a test journal entry",
        mood="Happy",
        entry_date=datetime.now(),
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)
    journal_id = journal.id
    db.close()
    return journal_id


@pytest.fixture(scope="function")
def journal_with_photos(client, test_user):
    """Create a journal with photos for cascade delete testing"""
    db = TestingSessionLocal()
    journal = Journal(
        user_id=test_user.id,
        title="Journal with Photos",
        content="Testing photo cascade delete",
        mood="Excited",
        entry_date=datetime.now(),
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)

    # Add photos
    photo1 = JournalPhoto(journal_id=journal.id, url="https://example.com/photo1.jpg")
    photo2 = JournalPhoto(journal_id=journal.id, url="https://example.com/photo2.jpg")
    db.add_all([photo1, photo2])
    db.commit()

    journal_id = journal.id
    db.close()
    return journal_id


def test_delete_journal_success(client, test_user, user_journal):
    """Test that a user can successfully delete their own journal"""
    response = client.delete(f"/api/v1/journal/{user_journal}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Journal entry deleted successfully"
    assert data["data"] is None

    # Verify journal is actually deleted from database
    db = TestingSessionLocal()
    deleted_journal = db.query(Journal).filter(Journal.id == user_journal).first()
    assert deleted_journal is None
    db.close()


def test_delete_journal_with_photos_cascade(client, test_user, journal_with_photos):
    """Test that deleting a journal also deletes associated photos (cascade delete)"""
    # Verify photos exist before deletion
    db = TestingSessionLocal()
    photos_before = (
        db.query(JournalPhoto)
        .filter(JournalPhoto.journal_id == journal_with_photos)
        .all()
    )
    assert len(photos_before) == 2
    db.close()

    # Delete journal
    response = client.delete(f"/api/v1/journal/{journal_with_photos}")
    assert response.status_code == 200

    # Verify journal and photos are deleted
    db = TestingSessionLocal()
    deleted_journal = (
        db.query(Journal).filter(Journal.id == journal_with_photos).first()
    )
    photos_after = (
        db.query(JournalPhoto)
        .filter(JournalPhoto.journal_id == journal_with_photos)
        .all()
    )

    assert deleted_journal is None
    assert len(photos_after) == 0  # Photos should be cascade deleted
    db.close()


def test_delete_journal_not_found(client, test_user):
    """Test deleting a non-existent journal returns 404"""
    random_id = uuid.uuid4()
    response = client.delete(f"/api/v1/journal/{random_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Journal entry not found"


def test_delete_journal_unauthorized_user(client):
    """Test that a user cannot delete another user's journal"""
    db = TestingSessionLocal()

    # Create two users
    user1 = User(full_name="User One", email="user1@test.com", is_active=True)
    user2 = User(full_name="User Two", email="user2@test.com", is_active=True)
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    # Create journal for user1
    journal = Journal(
        user_id=user1.id,
        title="User 1's Private Journal",
        content="This belongs to user 1",
        mood="Private",
        entry_date=datetime.now(),
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)
    journal_id = journal.id
    db.close()

    # Try to delete user1's journal as user2
    app.dependency_overrides[get_current_user] = lambda: user2
    response = client.delete(f"/api/v1/journal/{journal_id}")

    assert response.status_code == 404  # Should return 404 (not found/unauthorized)

    # Verify journal still exists
    db = TestingSessionLocal()
    existing_journal = db.query(Journal).filter(Journal.id == journal_id).first()
    assert existing_journal is not None
    assert existing_journal.title == "User 1's Private Journal"
    db.close()


def test_delete_journal_invalid_uuid(client, test_user):
    """Test that invalid UUID format returns proper error"""
    response = client.delete("/api/v1/journal/invalid-uuid-format")

    assert response.status_code == 422  # Validation error

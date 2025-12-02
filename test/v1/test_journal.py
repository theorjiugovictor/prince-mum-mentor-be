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
from api.v1.models.journal.journal_category import JournalCategory
from api.v1.models.journal.journal_photos import JournalPhoto
from api.utils.deps import get_current_user

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_journal.db"
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
    user = User(full_name="Test Mom", email="testmom@journal.com", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Override current user dependency
    app.dependency_overrides[get_current_user] = lambda: user
    db.close()
    return user


def test_create_journal_entry_without_category(client, test_user):
    """Test creating a journal entry without a category"""
    payload = {
        "title": "My First Day",
        "date": datetime.now().isoformat(),
        "thoughts": "Today was amazing! I felt so happy.",
        "mood": "Happy",
    }

    response = client.post("/api/v1/journal/entry/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Journal created successfully"
    assert "journal_entry_id" in data["data"]
    assert data["data"]["title"] == "My First Day"


def test_create_journal_entry_with_new_category(client, test_user):
    """Test creating a journal entry with a new category (should auto-create category)"""
    payload = {
        "title": "Delicious Meal",
        "date": datetime.now().isoformat(),
        "category": "Food",
        "thoughts": "I ate the best Jollof rice today!",
        "mood": "Satisfied",
    }

    response = client.post("/api/v1/journal/entry/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "journal_entry_id" in data["data"]

    # Verify category was created
    db = TestingSessionLocal()
    category = db.query(JournalCategory).filter(JournalCategory.name == "Food").first()
    assert category is not None
    assert category.name == "Food"

    # Verify journal is linked to category
    journal = (
        db.query(Journal)
        .filter(Journal.id == uuid.UUID(data["data"]["journal_entry_id"]))
        .first()
    )
    assert journal is not None
    assert journal.category_id == category.id
    db.close()


def test_create_journal_entry_with_existing_category(client, test_user):
    """Test creating a journal entry with an existing category (should reuse category)"""
    db = TestingSessionLocal()

    # Create category first
    existing_category = JournalCategory(name="Health")
    db.add(existing_category)
    db.commit()
    category_id = existing_category.id
    db.close()

    payload = {
        "title": "Morning Exercise",
        "date": datetime.now().isoformat(),
        "category": "Health",
        "thoughts": "Did 30 minutes of yoga today",
        "mood": "Energetic",
    }

    response = client.post("/api/v1/journal/entry/", json=payload)

    assert response.status_code == 201
    data = response.json()

    # Verify it used the existing category (not created a duplicate)
    db = TestingSessionLocal()
    categories = (
        db.query(JournalCategory).filter(JournalCategory.name == "Health").all()
    )
    assert len(categories) == 1  # Should only have one "Health" category
    assert categories[0].id == category_id

    # Verify journal is linked to existing category
    journal = (
        db.query(Journal)
        .filter(Journal.id == uuid.UUID(data["data"]["journal_entry_id"]))
        .first()
    )
    assert journal.category_id == category_id
    db.close()


def test_create_journal_entry_with_photos(client, test_user):
    """Test creating a journal entry with photo URLs"""
    payload = {
        "title": "Beach Day",
        "date": datetime.now().isoformat(),
        "category": "Travel",
        "photos": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        "thoughts": "Had an amazing time at the beach!",
        "mood": "Excited",
    }

    response = client.post("/api/v1/journal/entry/", json=payload)

    assert response.status_code == 201
    data = response.json()

    # Verify photos were saved
    db = TestingSessionLocal()
    journal_id = uuid.UUID(data["data"]["journal_entry_id"])
    photos = db.query(JournalPhoto).filter(JournalPhoto.journal_id == journal_id).all()

    assert len(photos) == 2
    photo_urls = [photo.url for photo in photos]
    assert "https://example.com/photo1.jpg" in photo_urls
    assert "https://example.com/photo2.jpg" in photo_urls
    db.close()


def test_create_journal_entry_all_fields(client, test_user):
    """Test creating a journal entry with all optional fields populated"""
    payload = {
        "title": "Complete Entry",
        "date": "2025-11-28T10:00:00Z",
        "category": "Personal",
        "mood": "Reflective",
        "photos": ["https://example.com/reflection.jpg"],
        "thoughts": "A day of deep reflection and gratitude.",
    }

    response = client.post("/api/v1/journal/entry/", json=payload)

    assert response.status_code == 201
    data = response.json()

    # Verify all fields were saved correctly
    db = TestingSessionLocal()
    journal = (
        db.query(Journal)
        .filter(Journal.id == uuid.UUID(data["data"]["journal_entry_id"]))
        .first()
    )

    assert journal is not None
    assert journal.title == "Complete Entry"
    assert journal.content == "A day of deep reflection and gratitude."
    assert journal.mood == "Reflective"
    assert journal.category is not None
    assert journal.category.name == "Personal"
    assert len(journal.photos) == 1
    db.close()


def test_create_journal_entry_missing_required_fields(client, test_user):
    """Test that creation fails when required fields are missing"""
    # Missing 'thoughts' field
    payload = {"title": "Incomplete Entry", "date": datetime.now().isoformat()}

    response = client.post("/api/v1/journal/entry/", json=payload)
    assert response.status_code == 422  # Validation error


def test_journal_entry_user_isolation(client):
    """Test that journals are properly isolated between users"""
    db = TestingSessionLocal()

    # Create two separate users
    user1 = User(full_name="User One", email="user1@test.com", is_active=True)
    user2 = User(full_name="User Two", email="user2@test.com", is_active=True)
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    # Create journal for user1
    app.dependency_overrides[get_current_user] = lambda: user1
    payload1 = {
        "title": "User 1 Journal",
        "date": datetime.now().isoformat(),
        "thoughts": "This is user 1's private journal",
        "category": "Private",
    }
    response1 = client.post("/api/v1/journal/entry/", json=payload1)
    assert response1.status_code == 201

    # Verify only user1's journal exists for them
    journals_user1 = db.query(Journal).filter(Journal.user_id == user1.id).all()
    journals_user2 = db.query(Journal).filter(Journal.user_id == user2.id).all()

    assert len(journals_user1) == 1
    assert len(journals_user2) == 0

    db.close()

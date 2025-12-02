import pytest
import uuid
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from api.db.base_model import Base
from api.db.database import get_db
from api.v1.models.user.user import User
from api.v1.models.journal.journal import Journal
from api.v1.dependencies.auth import get_current_user

TEST_DATABASE_URL = "sqlite:///./test_journal_new.db"
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
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_user(client):
    db = TestingSessionLocal()
    user = User(full_name="Journal User", email="j@test.com", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user
    return user


@pytest.fixture(scope="function")
def user_journal(client, test_user):
    db = TestingSessionLocal()
    journal = Journal(
        user_id=test_user.id,
        title="Old Title",
        content="Old content",
        mood="Sad",
        entry_date=datetime.now(),
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)
    j_id = journal.id
    db.close()
    return j_id


def test_edit_journal_success(client, test_user, user_journal):
    """Test editing title and mood"""
    payload = {
        "title": "New Happy Title",
        "mood": "Happy",
        "thoughts": "I am feeling better now",
        "category": "Health",
        "photos": ["http://img.com/1.jpg"],
    }

    response = client.patch(f"/api/v1/journal/{user_journal}", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Successfully edited entry"
    assert response.json()["data"]["title"] == "New Happy Title"


def test_edit_journal_not_found(client, test_user):
    """Test editing a non-existent journal returns 404"""
    random_id = uuid.uuid4()
    response = client.patch(f"/api/v1/journal/{random_id}", json={"title": "Fail"})
    assert response.status_code == 404

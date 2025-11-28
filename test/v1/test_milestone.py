import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, relationship
import uuid
from datetime import date

from main import app
from api.db.base_model import Base, BaseModel
from api.db.database import get_db
from api.v1.models.user.user import User, ProfileSetup, ChildProfile
from api.v1.models.milestones import Milestone
from api.utils.deps import get_current_user

class MilestoneCategory(BaseModel):
    __tablename__ = "milestone_categories"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[str] = mapped_column(String(100), default=lambda: str(uuid.uuid4()))
    owner_type: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(100))
    milestones = relationship("Milestone", back_populates="category")

TEST_DATABASE_URL = "sqlite:///./test_milestones.db"
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
    """Create the Mother"""
    db = TestingSessionLocal()
    user = User(full_name="Test Mom", email="mom@test.com", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    app.dependency_overrides[get_current_user] = lambda: user
    db.close()
    return user

@pytest.fixture(scope="function")
def test_category(client):
    """Create a Milestone Category (Required for FK)"""
    db = TestingSessionLocal()
    category = MilestoneCategory(
        name="Health", 
        description="Health related stuff",
        owner_id=str(uuid.uuid4()),
        owner_type="system"
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    db.close()
    return category

@pytest.fixture(scope="function")
def test_child(client, test_user):
    """Create a Child linked to the Mother"""
    db = TestingSessionLocal()
    
    profile = ProfileSetup(user_id=test_user.id, mom_status="New Mom", goals=[])
    db.add(profile)
    db.commit()
    db.refresh(profile)

    child = ChildProfile(
        profile_setup_id=profile.id,
        full_name="Baby Boy",
        date_of_birth=date.today()
    )
    db.add(child)
    db.commit()
    db.refresh(child)
    db.close()
    return child

def test_create_milestone_for_mother(client, test_user, test_category):
    """Test creating a milestone where owner is the Mother (Default)"""
    payload = {
        "name": "Mom's Yoga",
        "description": "Do yoga for 30 mins",
        "category_id": str(test_category.id)
    }
    
    response = client.post("/api/v1/milestones/", json=payload)
    
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["owner_type"] == "mother"
    assert data["owner_id"] == str(test_user.id)
    assert data["name"] == "Mom's Yoga"

def test_create_milestone_for_child(client, test_user, test_category, test_child):
    """Test creating a milestone where owner is the Child"""
    payload = {
        "name": "First Steps",
        "description": "Baby walked today",
        "category_id": str(test_category.id),
        "child_id": str(test_child.id)
    }
    
    response = client.post("/api/v1/milestones/", json=payload)
    
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["owner_type"] == "child"
    assert data["owner_id"] == str(test_child.id)

def test_create_milestone_unauthorized_child(client, test_user, test_category):
    """
    SECURITY TEST: Try to create a milestone for a random child ID 
    that does NOT belong to this user.
    """
    random_child_id = str(uuid.uuid4())
    
    payload = {
        "name": "Hacking Attempt",
        "category_id": str(test_category.id),
        "child_id": random_child_id
    }
    
    response = client.post("/api/v1/milestones/", json=payload)
    
    assert response.status_code == 404
    assert "does not belong to you" in response.json()["message"]

def test_toggle_milestone_status(client, test_user, test_category):
    """Test switching from pending to completed"""
    db = TestingSessionLocal()
    milestone = Milestone(
        name="Task 1", 
        owner_id=test_user.id, 
        owner_type="mother",
        category_id=test_category.id,
        status="pending"
    )
    db.add(milestone)
    db.commit()
    m_id = str(milestone.id)
    db.close()

    payload = {"completed": True}
    response = client.patch(f"/api/v1/milestones/{m_id}/status", json=payload)
    
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "completed"

    payload = {"completed": False}
    response = client.patch(f"/api/v1/milestones/{m_id}/status", json=payload)
    assert response.json()["data"]["status"] == "pending"

def test_get_pending_milestones_filter(client, test_user, test_category, test_child):
    """Test filtering pending milestones by child_id"""
    db = TestingSessionLocal()
    
    m1 = Milestone(name="Mom Task", owner_id=test_user.id, owner_type="mother", category_id=test_category.id, status="pending")
    m2 = Milestone(name="Baby Task", owner_id=test_child.id, owner_type="child", category_id=test_category.id, status="pending")
    
    db.add_all([m1, m2])
    db.commit()
    db.close()

    response_mom = client.get("/api/v1/milestones/pending")
    assert response_mom.status_code == 200
    assert len(response_mom.json()["data"]["details"]) == 1
    assert response_mom.json()["data"]["details"][0]["name"] == "Mom Task"

    response_child = client.get(f"/api/v1/milestones/pending?child_id={test_child.id}")
    assert response_child.status_code == 200
    assert len(response_child.json()["data"]["details"]) == 1
    assert response_child.json()["data"]["details"][0]["name"] == "Baby Task"
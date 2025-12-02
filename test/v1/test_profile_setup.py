import uuid
import pytest
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from api.db.database import get_db
from api.db.base_model import Base
from api.v1.models.user.user import User, ProfileSetup, ChildProfile
from api.utils.deps import get_current_user
from api.utils.security import hash_password

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


TEST_USER_ID = uuid.uuid4()


def override_get_current_user():
    """Return the test user for authentication override."""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == TEST_USER_ID).first()
    db.close()
    return user


# Override FastAPI deps
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Recreate tables and seed a user before each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create test user
    user = User(
        id=TEST_USER_ID,
        full_name="Test User",
        email="test@example.com",
        phone="+2348100000000",
        password_hash=hash_password("password123"),
        email_verified=True,
        phone_verified=True,
        is_active=True,
        role="user",
    )
    db.add(user)
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def pre_existing_profile():
    """Helper to create a profile BEFORE we try to update it"""
    payload = {
        "mom_status": "pregnant",
        "goals": ["Sleep"],
        "partner": {"name": "Dad", "email": "dad@test.com"},
        "children": [],
    }
    client.post("/api/v1/profile-setup/", json=payload)
    return payload


class TestProfileSetup:

    def test_create_profile_setup_success(self):
        """Success: profile setup is created correctly"""
        payload = {
            "mom_status": "pregnant",
            "goals": ["healthy pregnancy", "exercise"],
            "partner": {"name": "John Doe", "email": "partner@example.com"},
            "children": [
                {
                    "full_name": "Baby One",
                    "date_of_birth": "2020-01-01",
                    "gender": "female",
                }
            ],
        }

        response = client.post("/api/v1/profile-setup/", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["mom_status"] == "pregnant"
        assert len(data["data"]["children"]) == 1

    def test_create_profile_setup_duplicate(self):
        """Expected Error: creating profile twice returns 409"""
        payload = {
            "mom_status": "mixed",
            "goals": ["stay active"],
            "partner": None,
            "children": [],
        }

        # First attempt → success
        first = client.post("/api/v1/profile-setup/", json=payload)
        assert first.status_code == 201

        # Second attempt → 409 conflict
        second = client.post("/api/v1/profile-setup/", json=payload)
        assert second.status_code == 409

        data = second.json()
        assert data["status"] == "failure"
        assert "already been created" in data["message"]

    def test_create_profile_setup_invalid_payload(self):
        """Invalid Input: missing required fields triggers 422"""
        payload = {
            # mom_status missing!
            "goals": ["good health"]
        }

        response = client.post("/api/v1/profile-setup/", json=payload)
        assert response.status_code == 422

        data = response.json()
        assert "errors" in data["error"]

    def test_get_profile_setup_success(self, setup_database):
        """Success: returns the user's profile setup"""
        db = TestingSessionLocal()
        profile_setup = ProfileSetup(
            user_id=TEST_USER_ID,
            mom_status="toddler_mum",
            goals=["sleep", "eat"],
            partner={"name": "Test Partner", "email": "partner@example.com"},
        )
        db.add(profile_setup)
        db.commit()

        child = ChildProfile(
            profile_setup_id=profile_setup.id,
            full_name="Baby Doe",
            date_of_birth=date(2023, 1, 15),
            gender="F",
        )
        db.add(child)
        db.commit()
        db.close()

        response = client.get("/api/v1/profile-setup/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Profile setup retrieved successfully"
        assert data["data"]["user_id"] == str(TEST_USER_ID)
        assert data["data"]["mom_status"] == "toddler_mum"
        assert data["data"]["goals"] == ["sleep", "eat"]
        assert data["data"]["partner"]["name"] == "Test Partner"
        assert data["data"]["partner"]["email"] == "partner@example.com"
        assert len(data["data"]["children"]) == 1
        assert data["data"]["children"][0]["full_name"] == "Baby Doe"
        assert data["data"]["children"][0]["gender"] == "F"
        assert data["data"]["children"][0]["date_of_birth"] == "2023-01-15"

    def test_get_profile_setup_not_found(self, setup_database):
        """Not Found: returns 404 if profile setup does not exist"""
        response = client.get("/api/v1/profile-setup/")
        assert response.status_code == 404
        assert response.json()["message"] == "Profile setup not found"

    def test_get_profile_setup_unauthorized(self, setup_database):
        """Unauthorized: returns 401 if user is not authenticated"""
        from fastapi import HTTPException

        def raise_unauthorized():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_unauthorized

        response = client.get("/api/v1/profile-setup/")
        assert response.status_code in (401, 403)
        app.dependency_overrides[get_current_user] = override_get_current_user

    def test_update_children_list(self, setup_database, pre_existing_profile):
        """Test 2: Add a child (verify list replacement logic)"""

        patch_payload = {
            "children": [
                {
                    "full_name": "New Baby",
                    "gender": "male",
                    "date_of_birth": str(date.today()),
                }
            ]
        }

        response = client.patch("/api/v1/profile-setup/", json=patch_payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["children"]) == 1
        assert data["data"]["children"][0]["full_name"] == "New Baby"

        db = TestingSessionLocal()
        count = db.query(ChildProfile).count()
        assert count == 1
        db.close()

    def test_update_not_found(self, setup_database):
        """Test 3: Try to update a profile that doesn't exist yet"""
        patch_payload = {"mom_status": "mixed"}

        response = client.patch("/api/v1/profile-setup/", json=patch_payload)

        assert response.status_code == 404
        assert "Profile setup not found" in response.json()["message"]

    def test_remove_partner(self, setup_database, pre_existing_profile):
        """Test 4: Explicitly remove the partner by sending null"""
        patch_payload = {"partner": None}

        response = client.patch("/api/v1/profile-setup/", json=patch_payload)

        assert response.status_code == 200
        assert response.json()["data"]["partner"] is None

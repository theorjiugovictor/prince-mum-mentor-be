import uuid
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from api.db.database import get_db
from api.db.base_model import Base
from api.v1.models.user.user import User
from api.v1.models.resource.resource import Resource
from api.v1.models.resource.resource_category import ResourceCategory
from api.utils.deps import get_current_user
from api.utils.security import hash_password


SQLALCHEMY_DB_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
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
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == TEST_USER_ID).first()
    db.close()
    return user


# Override deps
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Recreate tables & seed user before each test."""
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    # Seed test user
    user = User(
        id=TEST_USER_ID,
        full_name="Tester",
        email="tester@example.com",
        phone="+2348012345678",
        password_hash=hash_password("password"),
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


def seed_resource(title: str, content="Sample content"):
    """
    Helper to insert a valid resource with a real category FK.
    """
    db = TestingSessionLocal()

    # Create a valid category first
    category = ResourceCategory(id=uuid.uuid4(), name="Test Category")
    db.add(category)
    db.commit()

    # Create resource linked to category
    item = Resource(title=title, content=content, category_id=category.id)

    db.add(item)
    db.commit()
    db.refresh(item)
    db.close()
    return item


class TestResourceSearch:

    def test_search_resources_success(self):
        """Should return matching resources"""
        seed_resource("Postpartum Care")
        seed_resource("Healthy Pregnancy Tips")

        response = client.get("/api/v1/resources/search?title=postpartum")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["total"] == 1
        assert data["data"]["data"][0]["title"] == "Postpartum Care"

    def test_search_resources_case_insensitive(self):
        """Search should be case-insensitive"""
        seed_resource("BREASTFEEDING GUIDE")

        response = client.get("/api/v1/resources/search?title=breast")

        assert response.status_code == 200
        assert response.json()["data"]["total"] == 1

    def test_search_resources_no_results(self):
        """404 returned when no matches found"""
        seed_resource("Baby Sleep Tips")

        response = client.get("/api/v1/resources/search?title=unknown")

        assert response.status_code == 404
        body = response.json()
        assert body["status"] == "failure"
        assert body["message"] == "No resources found"

    def test_search_resources_pagination(self):
        """Pagination should work correctly"""
        seed_resource("Feeding Guide 1")
        seed_resource("Feeding Guide 2")
        seed_resource("Feeding Guide 3")

        response = client.get("/api/v1/resources/search?title=feeding&page=1&limit=2")

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["page"] == 1
        assert data["limit"] == 2
        assert data["total"] == 3
        assert data["total_pages"] == 2
        assert len(data["data"]) == 2

    def test_search_resources_missing_title(self):
        """Validation error: missing title query param"""
        response = client.get("/api/v1/resources/search")

        assert response.status_code == 422
        assert response.json()["status"] == "failure"
        assert "Field required" in str(response.json())

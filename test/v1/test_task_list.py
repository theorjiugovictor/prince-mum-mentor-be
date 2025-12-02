import uuid
import pytest
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from api.db.database import get_db
from api.db.base_model import Base
from api.v1.models.user.user import User
from api.v1.models.task import Task
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
    """Return the test user"""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == TEST_USER_ID).first()
    db.close()
    return user


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create a test user
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


class TestListTasks:
    def test_list_tasks_success(self):
        """Success: returns tasks with correct pagination"""
        db = TestingSessionLocal()

        # Insert tasks
        for i in range(3):
            task = Task(
                user_id=TEST_USER_ID,
                name=f"Task {i}",
                description=f"Description {i}",
                status="pending",
                due_date=datetime.now(timezone.utc) + timedelta(days=i),
            )
            db.add(task)

        db.commit()
        db.close()

        response = client.get("/api/v1/tasks/?page=1&per_page=3&task_status=pending")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["details"]) == 3
        assert data["data"]["pagination"]["total_count"] == 3

    def test_list_tasks_invalid_input(self):
        """Invalid Input: invalid page/per_page triggers 422"""
        response = client.get("/api/v1/tasks/?page=-1&per_page=0")
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_list_tasks_unauthorized(self):
        """Expected Error: user not authenticated"""

        # Remove auth override to simulate no login
        app.dependency_overrides.pop(get_current_user, None)

        response = client.get("/api/v1/tasks/")
        assert response.status_code in (401, 403)

        # Restore auth override
        app.dependency_overrides[get_current_user] = override_get_current_user

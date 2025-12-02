import uuid
import pytest
from datetime import datetime, timezone

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
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


TEST_USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()


def override_get_current_user():
    """Override auth dependency for testing"""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == TEST_USER_ID).first()
    db.close()
    if user:
        return {"id": str(user.id)}
    return None


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup test database before each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    user = User(
        id=TEST_USER_ID,
        full_name="Test User",
        email="testuser@example.com",
        phone="+2348012345678",
        password_hash=hash_password("TestPassword123"),
        email_verified=True,
        phone_verified=True,
        is_active=True,
        role="user",
    )
    db.add(user)

    other_user = User(
        id=OTHER_USER_ID,
        full_name="Other User",
        email="otheruser@example.com",
        phone="+2348087654321",
        password_hash=hash_password("OtherPassword123"),
        email_verified=True,
        phone_verified=True,
        is_active=True,
        role="user",
    )
    db.add(other_user)

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


class TestToggleTaskCompletion:
    """Test cases for toggling task completion"""

    def test_mark_task_as_complete_success(self):
        """Test successfully marking a task as complete"""
        db = TestingSessionLocal()
        task = Task(user_id=TEST_USER_ID, name="Test Task", status="pending")
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        response = client.patch(
            f"/api/v1/tasks/{task_id}/status", json={"completed": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
        assert data["name"] == "Test Task"

    def test_mark_task_as_incomplete_success(self):
        """Test successfully marking a task as incomplete"""
        db = TestingSessionLocal()
        task = Task(
            user_id=TEST_USER_ID,
            name="Test Task",
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        response = client.patch(
            f"/api/v1/tasks/{task_id}/status", json={"completed": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["completed_at"] is None

    def test_toggle_task_not_found(self):
        """Test toggling a task that doesn't exist"""
        non_existent_id = uuid.uuid4()
        response = client.patch(
            f"/api/v1/tasks/{non_existent_id}/status", json={"completed": True}
        )
        assert response.status_code == 404

    def test_toggle_task_wrong_user(self):
        """Test toggling a task that belongs to another user"""
        db = TestingSessionLocal()
        task = Task(user_id=OTHER_USER_ID, name="Other User's Task", status="pending")
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        response = client.patch(
            f"/api/v1/tasks/{task_id}/status", json={"completed": True}
        )
        assert response.status_code == 404

    def test_toggle_task_invalid_uuid(self):
        """Test toggling task with invalid UUID"""
        response = client.patch(
            "/api/v1/tasks/invalid-uuid-format/status", json={"completed": True}
        )
        assert response.status_code == 422

    def test_toggle_task_no_authentication(self):
        """Test toggling task without authentication"""
        app.dependency_overrides[get_current_user] = lambda: None
        response = client.patch(
            f"/api/v1/tasks/{uuid.uuid4()}/status", json={"completed": True}
        )
        assert response.status_code == 401
        app.dependency_overrides[get_current_user] = override_get_current_user

    def test_updated_at_changes(self):
        """Test that updated_at timestamp changes after toggle"""
        db = TestingSessionLocal()
        task = Task(user_id=TEST_USER_ID, name="Test Task", status="pending")
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        original_updated_at = task.updated_at
        db.close()

        import time

        time.sleep(0.1)

        response = client.patch(
            f"/api/v1/tasks/{task_id}/status", json={"completed": True}
        )
        assert response.status_code == 200
        data = response.json()
        updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        assert updated_at > original_updated_at

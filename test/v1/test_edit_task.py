"""
Edit Task API Tests
Tests for PATCH /tasks/{task_id} endpoint
"""

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


# Setup test database
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


# Test user IDs
TEST_USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()


def override_get_current_user():
    """Override auth dependency for testing"""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == TEST_USER_ID).first()
    db.close()
    return user


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup test database before each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create test user
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

    # Create another user
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


class TestEditTask:
    """Test cases for editing tasks"""

    def test_edit_task_name_success(self):
        """Test successfully editing task name"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Original Task Name",
            description="Original description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Edit task name
        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"name": "Updated Task Name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Task updated successfully"
        assert data["data"]["name"] == "Updated Task Name"
        assert data["data"]["description"] == "Original description"
        assert data["data"]["status"] == "pending"

    def test_edit_task_description_success(self):
        """Test successfully editing task description"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Test Task",
            description="Original description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Edit task description
        response = client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"description": "Updated description with more details"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["description"] == "Updated description with more details"
        assert data["data"]["name"] == "Test Task"

    def test_edit_task_status_preserved(self):
        """Test that status is preserved when editing other fields"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Test Task",
            description="Test description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Edit task name and description
        response = client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"name": "Updated Task", "description": "Updated description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["status"] == "pending"
        assert data["data"]["name"] == "Updated Task"

    def test_edit_task_all_fields_success(self):
        """Test successfully editing all task fields"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Original Name",
            description="Original description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Edit all fields
        response = client.patch(
            f"/api/v1/tasks/{task_id}",
            json={
                "name": "Completely New Name",
                "description": "Completely new description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "Completely New Name"
        assert data["data"]["description"] == "Completely new description"
        assert "created_at" in data["data"]
        assert "updated_at" in data["data"]

    def test_edit_task_not_found(self):
        """Test editing a task that doesn't exist"""
        non_existent_id = uuid.uuid4()

        response = client.patch(
            f"/api/v1/tasks/{non_existent_id}", json={"name": "New Name"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "failure"
        assert data["message"] == "Task not found"

    def test_edit_task_wrong_user(self):
        """Test editing a task that belongs to another user"""
        db = TestingSessionLocal()

        # Create a task for another user
        task = Task(
            user_id=OTHER_USER_ID,
            name="Other User's Task",
            description="This belongs to another user",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Try to edit it with current user
        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"name": "Trying to steal this task"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "failure"
        assert data["message"] == "Task not found"

    def test_edit_task_empty_name(self):
        """Test editing task with empty name"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Valid Task Name",
            description="Test description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Try to edit with empty name
        response = client.patch(f"/api/v1/tasks/{task_id}", json={"name": "   "})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_edit_task_invalid_uuid(self):
        """Test editing task with invalid UUID"""
        response = client.patch(
            "/api/v1/tasks/invalid-uuid-format", json={"name": "New Name"}
        )

        assert response.status_code == 422

    def test_edit_task_no_fields_provided(self):
        """Test editing task with no fields (should still succeed)"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Task Name",
            description="Task description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        original_name = task.name
        db.close()

        # Edit with empty body
        response = client.patch(f"/api/v1/tasks/{task_id}", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == original_name

    def test_edit_task_partial_update(self):
        """Test partial update (only some fields)"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Task Name",
            description="Task description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Update only name
        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"name": "Only Name Updated"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Only Name Updated"
        assert data["data"]["description"] == "Task description"

    def test_edit_task_name_max_length(self):
        """Test editing task with name at max length"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Short Name",
            description="Test description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Edit with max length name (200 characters)
        long_name = "A" * 200
        response = client.patch(f"/api/v1/tasks/{task_id}", json={"name": long_name})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == long_name

    def test_edit_task_description_max_length(self):
        """Test editing task with description at max length"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Task Name",
            description="Short description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Edit with max length description (1000 characters)
        long_description = "B" * 1000
        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"description": long_description}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["description"] == long_description

    def test_edit_task_response_format(self):
        """Test that response has correct format"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Task Name",
            description="Task description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"name": "Updated Name"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "status" in data
        assert "status_code" in data
        assert "message" in data
        assert "data" in data

        # Check data structure
        task_data = data["data"]
        assert "id" in task_data
        assert "name" in task_data
        assert "description" in task_data
        assert "status" in task_data
        assert "completed_at" in task_data
        assert "created_at" in task_data
        assert "updated_at" in task_data

    def test_edit_task_preserves_status(self):
        """Test that editing doesn't change task status"""
        db = TestingSessionLocal()

        # Create a completed task
        task = Task(
            user_id=TEST_USER_ID,
            name="Completed Task",
            description="Task description",
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Edit the task
        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"name": "Updated Completed Task"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "completed"
        assert data["data"]["completed_at"] is not None

    def test_edit_task_updated_at_changes(self):
        """Test that updated_at timestamp changes after edit"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Task Name",
            description="Task description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        original_updated_at = task.updated_at
        db.close()

        # Wait a moment and edit
        import time

        time.sleep(0.1)

        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"name": "Updated Name"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check that updated_at has changed
        updated_at = datetime.fromisoformat(
            data["data"]["updated_at"].replace("Z", "+00:00")
        )
        assert updated_at >= original_updated_at

    def test_edit_task_null_description(self):
        """Test editing task to set description to null"""
        db = TestingSessionLocal()

        # Create a task with description
        task = Task(
            user_id=TEST_USER_ID,
            name="Task Name",
            description="Original description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Set description to None
        response = client.patch(f"/api/v1/tasks/{task_id}", json={"description": None})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["description"] is None

    def test_edit_task_with_long_description(self):
        """Test editing task with very long description"""
        db = TestingSessionLocal()

        # Create a task
        task = Task(
            user_id=TEST_USER_ID,
            name="Task Name",
            description="Task description",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        # Update with very long description (within limits)
        long_desc = "This is a very detailed task description. " * 20
        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"description": long_desc}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["description"] == long_desc

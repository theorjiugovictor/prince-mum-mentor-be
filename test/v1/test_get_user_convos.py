"""
AI Chat Conversation API Tests
Tests for GET /chats/{convo_id} endpoint
"""

import uuid
from datetime import datetime, timezone
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from api.db.database import get_db
from api.db.base_model import Base
from api.v1.models.user.user import User
from api.v1.models.chat_session import ChatSession
from api.v1.models.chat_message import ChatMessage
from api.utils.security import hash_password
from api.utils.auth_utils import create_access_token


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
TEST_CONVO_ID = uuid.uuid4()
OTHER_CONVO_ID = uuid.uuid4()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup test database before each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create test users
    test_user = User(
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
    db.add(test_user)

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

    # Create test conversations
    test_session = ChatSession(
        id=TEST_CONVO_ID,
        user_id=TEST_USER_ID,
        title="My Test Conversation",
        created_at=datetime.now(timezone.utc),
    )
    db.add(test_session)

    other_session = ChatSession(
        id=OTHER_CONVO_ID,
        user_id=OTHER_USER_ID,
        title="Other User's Conversation",
        created_at=datetime.now(timezone.utc),
    )
    db.add(other_session)

    # Create test messages for the test conversation
    for i in range(25):  # Create 25 messages to test pagination
        sender = "user" if i % 2 == 0 else "ai"
        message = ChatMessage(
            session_id=TEST_CONVO_ID,
            sender=sender,
            message=f"Test message {i + 1}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(message)

    # Create one message for other user's conversation
    message = ChatMessage(
        session_id=OTHER_CONVO_ID,
        sender="user",
        message="Other user's message",
        created_at=datetime.now(timezone.utc),
    )
    db.add(message)

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


class TestGetUserConvos:
    """Test cases for get user conversations endpoint"""

    def test_get_conversation_success(self):
        """Test successfully retrieving a conversation with default pagination"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Conversation retrieved successfully"

        # Check conversation details
        assert data["data"]["conversation"]["id"] == str(TEST_CONVO_ID)
        assert data["data"]["conversation"]["user_id"] == str(TEST_USER_ID)
        assert data["data"]["conversation"]["title"] == "My Test Conversation"
        assert "created_at" in data["data"]["conversation"]

        # Check messages (default: page 1, per_page 20)
        assert len(data["data"]["messages"]) == 20
        assert data["data"]["messages"][0]["message"] == "Test message 1"

        # Check pagination
        assert data["data"]["pagination"]["page"] == 1
        assert data["data"]["pagination"]["per_page"] == 20
        assert data["data"]["pagination"]["total_count"] == 25
        assert data["data"]["pagination"]["total_pages"] == 2
        assert data["data"]["pagination"]["next"] == 2
        assert data["data"]["pagination"]["prev"] is None

    def test_get_conversation_with_pagination(self):
        """Test retrieving conversation with custom pagination"""
        access_token = create_access_token(TEST_USER_ID, "user")

        # Get page 2 with 10 items per page
        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}?page=2&per_page=10",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check messages (should get messages 11-20)
        assert len(data["data"]["messages"]) == 10
        assert data["data"]["messages"][0]["message"] == "Test message 11"

        # Check pagination
        assert data["data"]["pagination"]["page"] == 2
        assert data["data"]["pagination"]["per_page"] == 10
        assert data["data"]["pagination"]["total_count"] == 25
        assert data["data"]["pagination"]["total_pages"] == 3
        assert data["data"]["pagination"]["next"] == 3
        assert data["data"]["pagination"]["prev"] == 1

    def test_get_conversation_last_page(self):
        """Test retrieving last page of conversation"""
        access_token = create_access_token(TEST_USER_ID, "user")

        # Get page 3 with 10 items per page (last page has 5 items)
        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}?page=3&per_page=10",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check messages (should get last 5 messages)
        assert len(data["data"]["messages"]) == 5
        assert data["data"]["messages"][0]["message"] == "Test message 21"

        # Check pagination
        assert data["data"]["pagination"]["next"] is None
        assert data["data"]["pagination"]["prev"] == 2

    def test_get_conversation_not_found(self):
        """Test retrieving non-existent conversation"""
        access_token = create_access_token(TEST_USER_ID, "user")
        non_existent_id = uuid.uuid4()

        response = client.get(
            f"/api/v1/chats/{non_existent_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found"

    def test_get_conversation_forbidden(self):
        """Test accessing another user's conversation"""
        access_token = create_access_token(TEST_USER_ID, "user")

        # Try to access OTHER_USER's conversation
        response = client.get(
            f"/api/v1/chats/{OTHER_CONVO_ID}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"] == "You do not have access to this conversation"
        )

    def test_get_conversation_no_token(self):
        """Test accessing conversation without authentication"""
        response = client.get(f"/api/v1/chats/{TEST_CONVO_ID}")

        assert response.status_code == 401

    def test_get_conversation_invalid_token(self):
        """Test accessing conversation with invalid token"""
        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    def test_get_conversation_invalid_uuid(self):
        """Test using invalid UUID format"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            "/api/v1/chats/not-a-valid-uuid",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # FastAPI returns 400 for invalid UUID in path
        assert response.status_code in [400, 422]

    def test_get_conversation_pagination_boundaries(self):
        """Test pagination with boundary values"""
        access_token = create_access_token(TEST_USER_ID, "user")

        # Test with page < 1 (should fail validation)
        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}?page=0",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code in [400, 422]

        # Test with per_page > 100 (should fail validation)
        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}?per_page=101",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code in [400, 422]

        # Test with per_page < 1 (should fail validation)
        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}?per_page=0",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code in [400, 422]

    def test_get_conversation_max_per_page(self):
        """Test with maximum allowed per_page value"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}?per_page=100",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["messages"]) == 25  # All messages fit in one page
        assert data["data"]["pagination"]["per_page"] == 100

    def test_message_data_structure(self):
        """Test that message data has correct structure"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check first message structure
        message = data["data"]["messages"][0]
        assert "id" in message
        assert "sender" in message
        assert "message" in message
        assert "created_at" in message
        assert message["sender"] in ["user", "ai"]

    def test_messages_order(self):
        """Test that messages are ordered by creation time (ascending)"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        messages = data["data"]["messages"]
        # First message should be "Test message 1"
        assert messages[0]["message"] == "Test message 1"
        # Second message should be "Test message 2"
        assert messages[1]["message"] == "Test message 2"

    def test_empty_conversation(self):
        """Test retrieving conversation with no messages"""
        access_token = create_access_token(TEST_USER_ID, "user")

        # Create a new conversation with no messages
        db = TestingSessionLocal()
        empty_convo_id = uuid.uuid4()
        empty_session = ChatSession(
            id=empty_convo_id,
            user_id=TEST_USER_ID,
            title="Empty Conversation",
            created_at=datetime.now(timezone.utc),
        )
        db.add(empty_session)
        db.commit()
        db.close()

        response = client.get(
            f"/api/v1/chats/{empty_convo_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["messages"]) == 0
        assert data["data"]["pagination"]["total_count"] == 0
        assert data["data"]["pagination"]["total_pages"] == 1

    def test_response_format(self):
        """Test that response follows standard format"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            f"/api/v1/chats/{TEST_CONVO_ID}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check standard response structure
        assert "status" in data
        assert "status_code" in data
        assert "message" in data
        assert "data" in data

        # Check data structure
        assert "conversation" in data["data"]
        assert "messages" in data["data"]
        assert "pagination" in data["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

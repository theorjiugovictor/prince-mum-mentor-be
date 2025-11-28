import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from main import app

from api.db.base_model import Base
from api.db.database import get_db
from api.v1.models.user.user import User

from api.utils.deps import get_current_user
from api.v1.models.chat_message import ChatMessage
from api.v1.models.chat_session import ChatSession

TEST_DATABASE_URL = "sqlite:///./test_chat_delete.db"
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
    """Setup test DB and Client"""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_user(client):
    """Create a user and force auth to use it"""
    db = TestingSessionLocal()
    user = User(full_name="Test User", email="test@user.com", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    
    app.dependency_overrides[get_current_user] = lambda: user
    return user

@pytest.fixture(scope="function")
def user_chat(client, test_user):
    """Create a chat session belonging to the test user"""
    db = TestingSessionLocal()
    chat = ChatSession(user_id=test_user.id, title="Test Conversation")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    chat_id = chat.id
    db.close()
    return chat_id

def test_delete_conversation_success(client, test_user, user_chat):
    """
    Requirement: When a valid conversation ID is provided, 
    the conversation is successfully deleted.
    """
    response = client.delete(f"/api/v1/ai-chat/chats/{user_chat}")

    assert response.status_code == 200
    assert response.json()["message"] == "Conversation deleted"

    db = TestingSessionLocal()
    exists = db.query(ChatSession).filter(ChatSession.id == user_chat).first()
    db.close()
    assert exists is None

def test_delete_conversation_not_found(client, test_user):
    """
    Requirement: If the conversation does not exist, 
    return 404 Conversation Not Found.
    """
    random_id = uuid.uuid4()
    
    response = client.delete(f"/api/v1/ai-chat/chats/{random_id}")

    assert response.status_code == 404
    assert response.json()["message"] == "Conversation not found"

def test_delete_conversation_idempotency(client, test_user, user_chat):
    """
    Requirement: Repeating delete returns 404 after first deletion.
    """
    response_1 = client.delete(f"/api/v1/ai-chat/chats/{user_chat}")
    assert response_1.status_code == 200

    response_2 = client.delete(f"/api/v1/ai-chat/chats/{user_chat}")
    assert response_2.status_code == 404
    assert response_2.json()["message"] == "Conversation not found"

def test_delete_other_users_chat(client, test_user):
    """
    Requirement: Must verify that the conversation belongs to the requesting user.
    If not, it should behave like a 404 (Security).
    """
    db = TestingSessionLocal()
 
    other_user = User(full_name="Other User", email="other@user.com", is_active=True)
    db.add(other_user)
    db.commit()
    
    other_chat = ChatSession(user_id=other_user.id, title="Secret Chat")
    db.add(other_chat)
    db.commit()
    other_chat_id = other_chat.id
    db.close()

    response = client.delete(f"/api/v1/ai-chat/chats/{other_chat_id}")

    assert response.status_code == 404
    assert response.json()["message"] == "Conversation not found"
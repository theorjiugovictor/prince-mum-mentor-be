import uuid
import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from fastapi import HTTPException

from main import app
from api.v1.models.user.user import User
from api.db.database import get_db
from api.utils.deps import get_current_user

client = TestClient(app)


@pytest.fixture
def mock_db_session():
    """Return a mock DB session and ensure dependency overrides are cleared."""
    session = MagicMock()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()


def _make_user():
    """Helper to create a mock user"""
    return User(
        id=uuid.uuid4(),
        email="testuser@community.com",
        full_name="Test User",
        role="user",
        password_hash="hash",
        is_active=True,
    )


def test_like_post_success(mock_db_session, monkeypatch):
    """Test successfully liking a post"""
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    post_id = uuid.uuid4()

    # Mock service to return (True, 1) indicating post is now liked with 1 total like
    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.toggle_post_like",
        lambda session, post_id, user_id: (True, 1),
    )

    response = client.post(f"/api/v1/community/posts/{post_id}/like")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["message"] == "Post liked successfully"
    assert body["data"]["is_liked"] is True
    assert body["data"]["likes_count"] == 1


def test_unlike_post_success(mock_db_session, monkeypatch):
    """Test successfully unliking a post that was previously liked"""
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    post_id = uuid.uuid4()

    # Mock service to return (False, 0) indicating post is now unliked with 0 total likes
    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.toggle_post_like",
        lambda session, post_id, user_id: (False, 0),
    )

    response = client.post(f"/api/v1/community/posts/{post_id}/like")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["message"] == "Post unliked successfully"
    assert body["data"]["is_liked"] is False
    assert body["data"]["likes_count"] == 0


def test_toggle_like_multiple_users(mock_db_session, monkeypatch):
    """Test that multiple users can like the same post"""
    user1 = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user1

    post_id = uuid.uuid4()

    # User 1 likes the post
    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.toggle_post_like",
        lambda session, post_id, user_id: (True, 1),
    )

    response1 = client.post(f"/api/v1/community/posts/{post_id}/like")
    assert response1.status_code == 200
    assert response1.json()["data"]["is_liked"] is True
    assert response1.json()["data"]["likes_count"] == 1

    # User 2 also likes the post (count should be 2)
    user2 = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user2

    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.toggle_post_like",
        lambda session, post_id, user_id: (True, 2),
    )

    response2 = client.post(f"/api/v1/community/posts/{post_id}/like")
    assert response2.status_code == 200
    assert response2.json()["data"]["is_liked"] is True
    assert response2.json()["data"]["likes_count"] == 2


def test_like_post_not_found(mock_db_session, monkeypatch):
    """Test liking a non-existent post returns 404"""
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    post_id = uuid.uuid4()

    # Mock service to raise HTTPException for post not found
    def raise_404(session, post_id, user_id):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.toggle_post_like",
        raise_404,
    )

    response = client.post(f"/api/v1/community/posts/{post_id}/like")

    assert response.status_code == 404
    response_json = response.json()
    # Check for either 'detail' (standard FastAPI) or 'message' (custom error handler)
    assert "message" in response_json or "detail" in response_json
    error_msg = response_json.get("message") or response_json.get("detail")
    assert "Post not found" in error_msg


def test_toggle_like_same_user_twice(mock_db_session, monkeypatch):
    """Test toggling like twice (like then unlike)"""
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    post_id = uuid.uuid4()

    # First call: like the post
    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.toggle_post_like",
        lambda session, post_id, user_id: (True, 1),
    )

    response1 = client.post(f"/api/v1/community/posts/{post_id}/like")
    assert response1.json()["data"]["is_liked"] is True

    # Second call: unlike the post
    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.toggle_post_like",
        lambda session, post_id, user_id: (False, 0),
    )

    response2 = client.post(f"/api/v1/community/posts/{post_id}/like")
    assert response2.json()["data"]["is_liked"] is False
    assert response2.json()["data"]["likes_count"] == 0

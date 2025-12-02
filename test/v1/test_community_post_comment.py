
import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from api.v1.models.user.user import User
from api.v1.models.community.posts import Post
from api.db.database import get_db
from api.utils.deps import get_current_user

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    session = MagicMock()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()

def _make_user():
    return User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        full_name="Test User",
        role="user",
        password_hash="hash",
        is_active=True,
    )

def _make_post(user_id=None):
    return Post(
        id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        title="Test Post",
        content="Test content."
    )

def test_comment_on_post_success(mock_db_session, monkeypatch):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    post = _make_post(user_id=user.id)

    class DummyComment:
        id = uuid.uuid4()
        comment = "This is a test comment."

    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.add_comment_to_post",
        lambda session, post_id, user_id, comment: DummyComment(),
    )

    payload = {"comment": "This is a test comment."}
    response = client.post(f"/api/v1/community/posts/{post.id}/comment", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Comment added successfully"
    assert body["data"]["comment"] == "This is a test comment."


def test_comment_on_post_not_found(mock_db_session, monkeypatch):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    random_post_id = uuid.uuid4()

    def raise_not_found(session, post_id, user_id, comment):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")

    monkeypatch.setattr(
        "api.v1.services.community.CommunityService.add_comment_to_post",
        raise_not_found,
    )

    payload = {"comment": "This is a test comment."}
    response = client.post(f"/api/v1/community/posts/{random_post_id}/comment", json=payload)
    assert response.status_code == 404
    assert "Post not found" in response.text


def test_comment_on_post_unauthenticated(mock_db_session, monkeypatch):
    post = _make_post()
    # No user override
    payload = {"comment": "This is a test comment."}
    response = client.post(f"/api/v1/community/posts/{post.id}/comment", json=payload)
    assert response.status_code in (401, 403)

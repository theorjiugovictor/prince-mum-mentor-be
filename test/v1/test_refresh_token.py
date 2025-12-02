import pytest
import uuid
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient

from main import app
from api.v1.models.user.user import User, UserAuthSession
from api.db.database import get_db
from api.utils.auth_utils import generate_refresh_token
from api.v1.services.refresh_service import _hash_token

client = TestClient(app)


@pytest.fixture
def mock_db_session():
    """Return a mock DB session and register it as the FastAPI dependency."""
    session = MagicMock()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()


def _make_query_return(obj):
    q = MagicMock()
    q.filter.return_value.first.return_value = obj
    return q


def test_refresh_success(mock_db_session):
    # Prepare user and session objects
    user = User(id=uuid.uuid4(), full_name="Test User", email="test@example.com")
    token = generate_refresh_token(subject=user.id)
    session_obj = UserAuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token=_hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=False,
    )

    # Map model -> query result so mock_session.query(Model) works
    mapping = {
        UserAuthSession: session_obj,
        User: user,
    }

    mock_db_session.query.side_effect = lambda model: _make_query_return(
        mapping.get(model)
    )

    resp = client.post(
        "/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]


def test_refresh_invalid_token(mock_db_session):
    # query returns None for session
    mock_db_session.query.side_effect = lambda model: _make_query_return(None)
    resp = client.post(
        "/api/v1/auth/refresh", headers={"Authorization": "Bearer invalid"}
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["status"] == "failure"


def test_refresh_missing_header(mock_db_session):
    # No Authorization header should be rejected
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
    body = resp.json()
    assert body["status"] == "failure"


def test_refresh_null_header(mock_db_session):
    # Null/empty token in header -> invalid
    resp = client.post("/api/v1/auth/refresh", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


def test_refresh_revoked_token(mock_db_session):
    user = User(id=uuid.uuid4(), full_name="Revoked", email="revoked@example.com")
    token = generate_refresh_token(subject=user.id)
    session_obj = UserAuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token=_hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        is_revoked=True,
    )

    mapping = {UserAuthSession: session_obj, User: user}
    mock_db_session.query.side_effect = lambda model: _make_query_return(
        mapping.get(model)
    )

    resp = client.post(
        "/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["status"] == "failure"


def test_refresh_expired_token(mock_db_session):
    user = User(id=uuid.uuid4(), full_name="Expired", email="expired@example.com")
    token = generate_refresh_token(subject=user.id)
    session_obj = UserAuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token=_hash_token(token),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        is_revoked=False,
    )

    mapping = {UserAuthSession: session_obj, User: user}
    mock_db_session.query.side_effect = lambda model: _make_query_return(
        mapping.get(model)
    )

    resp = client.post(
        "/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["status"] == "failure"
    # repeated request also fails
    resp = client.post(
        "/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

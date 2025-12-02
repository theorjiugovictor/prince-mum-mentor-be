import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from main import app
from api.v1.models.user.user import User
from api.db.database import get_db

client = TestClient(app)


@pytest.fixture
def mock_db_session(mocker):
    """Return a mock DB session."""
    session = MagicMock()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()


def test_login_success(mock_db_session, mocker):
    mocker.patch("api.v1.routes.auth.login.verify_password", return_value=True)
    mocker.patch(
        "api.v1.routes.auth.login.create_access_token", return_value="access123"
    )
    mocker.patch(
        "api.v1.routes.auth.login.create_refresh_token", return_value="refresh123"
    )

    user_obj = User(
        id="123",
        email="test@example.com",
        full_name="Tester Joe",
        role="user",
        password_hash="$2b$12$abcdefghijklmnopqrstuv",
        is_active=True,
    )

    mock_db_session.query.return_value.filter.return_value.first.return_value = user_obj

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "correctpass"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]


def test_login_invalid_password(mock_db_session, mocker):
    mocker.patch("api.v1.routes.auth.login.verify_password", return_value=False)

    user_obj = User(
        id="123",
        email="test@example.com",
        full_name="Tester Joe",
        role="user",
        password_hash="hashedpassword",
        is_active=True,
    )

    mock_db_session.query.return_value.filter.return_value.first.return_value = user_obj

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpass"},
    )

    assert response.status_code == 401


def test_login_nonexistent_user(mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.post(
        "/api/v1/auth/login", json={"email": "nobody@nowhere.com", "password": "abc"}
    )

    assert response.status_code == 404


def test_login_invalid_payload():
    response = client.post("/api/v1/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422


def test_login_inactive_user(mock_db_session, mocker):
    """Test login with inactive user account - should be treated as not found."""
    mocker.patch("api.v1.routes.auth.login.verify_password", return_value=True)

    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "correctpass"},
    )
    assert response.status_code == 404


def test_login_response_structure(mock_db_session, mocker):
    """Test response contains correct structure."""
    mocker.patch("api.v1.routes.auth.login.verify_password", return_value=True)
    mocker.patch(
        "api.v1.routes.auth.login.create_access_token", return_value="access123"
    )
    mocker.patch(
        "api.v1.routes.auth.login.create_refresh_token", return_value="refresh123"
    )

    user_obj = User(
        id="123",
        email="test@example.com",
        full_name="Tester Joe",
        role="user",
        password_hash="$2b$12$abcdefghijklmnopqrstuv",
        is_active=True,
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = user_obj

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "correctpass"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert body["data"]["access_token"] == "access123"
    assert body["data"]["refresh_token"] == "refresh123"


def test_login_email_case_insensitive(mock_db_session, mocker):
    """Test login with different email cases."""
    mocker.patch("api.v1.routes.auth.login.verify_password", return_value=True)
    mocker.patch(
        "api.v1.routes.auth.login.create_access_token", return_value="access123"
    )
    mocker.patch(
        "api.v1.routes.auth.login.create_refresh_token", return_value="refresh123"
    )

    user_obj = User(
        id="123",
        email="test@example.com",
        full_name="Tester Joe",
        role="user",
        password_hash="hash",
        is_active=True,
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = user_obj

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "TEST@EXAMPLE.COM", "password": "correctpass"},
    )
    assert response.status_code == 200

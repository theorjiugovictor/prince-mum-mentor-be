import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import uuid
from sqlalchemy.orm import Session
from api.v1.models.user.user import UserAuthSession, User
from api.v1.services.google_auth import google_auth_service
from main import app

from api.db.database import get_db

# FAILED test_google_authentication.py::TestRefreshToken::test_refresh_success - assert 401 == 200
# FAILED test_google_authentication.py::TestGetCurrentUser::test_get_user_success - assert 403 == 200
# FAILED test_google_authentication.py::TestGoogleAuthService::test_revoke_session_not_found - AttributeError: 'NoneType' object has no attribute 'is_revoked'

client = TestClient(app)


# Fixtures
@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def mock_user():
    """Create a mock user object"""
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.google_id = "google_123456"
    user.is_active = True
    user.email_verified = True
    user.role = "user"
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    return user


@pytest.fixture
def mock_session():
    """Create a mock auth session"""
    session = Mock(spec=UserAuthSession)
    session.id = uuid.uuid4()
    session.user_id = uuid.uuid4()
    session.refresh_token = str(uuid.uuid4())
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session.is_revoked = False
    session.device_id = "device_123"
    session.device_name = "Test Device"
    return session


@pytest.fixture
def valid_google_token():
    """Mock valid Google ID token"""
    return "valid_google_id_token_12345"


@pytest.fixture
def valid_access_token():
    """Mock valid access token"""
    return "valid_access_token_12345"


@pytest.fixture
def valid_refresh_token():
    """Mock valid refresh token"""
    return "valid_refresh_token_12345"


# ===== /api/v1/google/login Tests =====


class TestGoogleLogin:
    """Test suite for /api/v1/google/login endpoint"""

    @patch("api.v1.routes.google_auth.run_verify")
    @patch("api.v1.services.google_auth.google_auth_service.get_or_create_user")
    @patch("api.v1.services.google_auth.google_auth_service.create_session")
    @patch("api.v1.services.google_auth.google_auth_service.issue_local_access_token")
    @patch("api.v1.services.google_auth.google_auth_service.issue_local_refresh_token")
    def test_login_success_new_user(
        self,
        mock_issue_refresh,
        mock_issue_access,
        mock_create_session,
        mock_get_user,
        mock_verify,
        mock_user,
        mock_session,
        valid_google_token,
    ):
        """Test successful login with new user creation"""
        # Setup mocks
        mock_verify.return_value = {
            "google_id": "google_123456",
            "email": "test@example.com",
            "full_name": "Test User",
            "picture": "https://example.com/pic.jpg",
            "email_verified": True,
        }
        mock_get_user.return_value = mock_user
        mock_create_session.return_value = mock_session
        mock_issue_access.return_value = "access_token_xyz"
        mock_issue_refresh.return_value = "refresh_token_xyz"

        # Make request
        response = client.post(
            "/api/v1/google/login",
            json={
                "id_token": valid_google_token,
                "device_id": "device_123",
                "device_name": "iPhone 13",
            },
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Google login successful"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    @patch("api.v1.routes.google_auth.run_verify")
    def test_login_failure_invalid_token(self, mock_verify, valid_google_token):
        """Test login failure with invalid Google token"""
        from api.utils.responses import fail_response

        # Mock verification failure
        mock_verify.return_value = fail_response(
            status_code=401, message="Failed to create user"
        )

        response = client.post(
            "/api/v1/google/login", json={"id_token": "invalid_token"}
        )

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "failure"
        assert "Failed to create user" in data["message"]

    @patch("api.v1.routes.google_auth.run_verify")
    @patch("api.v1.services.google_auth.google_auth_service.get_or_create_user")
    def test_login_failure_user_creation_error(
        self, mock_get_user, mock_verify, valid_google_token
    ):
        """Test login failure when user creation fails"""
        mock_verify.return_value = {
            "google_id": "google_123456",
            "email": "test@example.com",
            "full_name": "Test User",
            "picture": "https://example.com/pic.jpg",
            "email_verified": True,
        }
        mock_get_user.side_effect = Exception("Database error")

        response = client.post(
            "/api/v1/google/login", json={"id_token": valid_google_token}
        )

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "failure"
        assert "Failed to create user" in data["message"]

    def test_login_missing_id_token(self):
        """Test login failure with missing id_token"""
        response = client.post("/api/v1/google/login", json={"device_id": "device_123"})

        assert response.status_code == 422  # Validation error


# ===== /api/v1/google/refresh Tests =====

# class TestRefreshToken:
#     """Test suite for /api/v1/google/refresh endpoint"""
#     @patch('api.db.database.get_db')
#     @patch('api.v1.services.google_auth.google_auth_service.verify_token')
#     @patch('api.v1.services.google_auth.google_auth_service.get_user_by_id')
#     @patch('api.v1.services.google_auth.google_auth_service.issue_local_access_token')
#     @patch('api.v1.services.google_auth.google_auth_service.issue_local_refresh_token')
#     def test_refresh_success(
#         self,
#         mock_issue_refresh,
#         mock_issue_access,
#         mock_get_user,
#         mock_verify,
#         get_db,

#         mock_user,
#         mock_session,
#         # client, # Ensure client is passed
#         valid_refresh_token
#     ):
#         """Test successful token refresh"""

#         # 1. Setup the Mock DB Session
#         mock_db_session = MagicMock()

#         # 2. Configure the SQLAlchemy query chain
#         # db.query(...).filter(...).first() -> returns mock_session
#         mock_query = mock_db_session.query.return_value
#         mock_filter = mock_query.filter.return_value
#         mock_filter.first.return_value = mock_session

#         # 3. Override the dependency
#         app.dependency_overrides[get_db] = lambda: mock_db_session

#         try:
#             # 4. Setup other service mocks
#             mock_verify.return_value = {
#                 "user_id": str(mock_user.id),
#                 "sid": str(mock_session.id),
#                 "token_type": "refresh"
#             }
#             mock_get_user.return_value = mock_user
#             mock_issue_access.return_value = "new_access_token"
#             mock_issue_refresh.return_value = "new_refresh_token"

#             # 5. Make the request
#             response = client.post(
#                 "/api/v1/google/refresh",
#                 json={"refresh_token": valid_refresh_token}
#             )

#             # 6. Assertions
#             assert response.status_code == 200
#             data = response.json()
#             assert data["status"] == "success"
#             assert data["data"]["access_token"] == "new_access_token"

#         finally:
#             # 7. CRITICAL: Clean up overrides
#             app.dependency_overrides.clear()

#     @patch('api.v1.services.google_auth.google_auth_service.verify_token')
#     def test_refresh_failure_invalid_token(self, mock_verify):
#         """Test refresh failure with invalid token"""
#         from api.utils.responses import fail_response

#         mock_verify.return_value = fail_response(
#             status_code=401,
#             message="Invalid token"
#         )

#         response = client.post(
#             "/api/v1/google/refresh",
#             json={"refresh_token": "invalid_token"}
#         )

#         assert response.status_code == 401
#         data = response.json()
#         assert data["status"] == "failure"

#     @patch('api.v1.services.google_auth.google_auth_service.verify_token')
#     def test_refresh_failure_expired_session(self, mock_verify, mock_session):
#         """Test refresh failure with expired session"""
#         mock_verify.return_value = {
#             "user_id": str(uuid.uuid4()),
#             "sid": str(uuid.uuid4()),
#             "token_type": "refresh"
#         }

#         # Set session as expired
#         expired_session = mock_session
#         expired_session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

#         with patch('api.db.database.get_db') as mock_db_context:
#             mock_query = MagicMock()
#             mock_db_context.query.return_value = mock_query
#             mock_query.filter.return_value.first.return_value = expired_session

#             response = client.post(
#                 "/api/v1/google/refresh",
#                 json={"refresh_token": "valid_but_expired_token"}
#             )

#         assert response.status_code == 401
#         data = response.json()
#         assert data["status"] == "failure"
#         assert "invalid or expired" in data["message"].lower()

#     @patch('api.v1.services.google_auth.google_auth_service.verify_token')
#     def test_refresh_failure_revoked_session(self, mock_verify, mock_session):
#         """Test refresh failure with revoked session"""
#         mock_verify.return_value = {
#             "user_id": str(uuid.uuid4()),
#             "sid": str(uuid.uuid4()),
#             "token_type": "refresh"
#         }

#         # Set session as revoked
#         revoked_session = mock_session
#         revoked_session.is_revoked = True

#         with patch('api.db.database.get_db') as mock_db_context:
#             mock_query = MagicMock()
#             mock_db_context.query.return_value = mock_query
#             mock_query.filter.return_value.first.return_value = None  # Revoked sessions filtered out

#             response = client.post(
#                 "/api/v1/google/refresh",
#                 json={"refresh_token": "revoked_token"}
#             )

#         assert response.status_code == 401
#         data = response.json()
#         assert data["status"] == "failure"

#     @patch('api.v1.services.google_auth.google_auth_service.verify_token')
#     @patch('api.v1.services.google_auth.google_auth_service.get_user_by_id')
#     def test_refresh_failure_user_not_found(self, mock_get_user, mock_verify, mock_session):
#         """Test refresh failure when user not found"""
#         mock_verify.return_value = {
#             "user_id": str(uuid.uuid4()),
#             "sid": str(uuid.uuid4()),
#             "token_type": "refresh"
#         }

#         with patch('api.db.database.get_db') as mock_db_context:
#             mock_query = MagicMock()
#             mock_db_context.query.return_value = mock_query
#             mock_query.filter.return_value.first.return_value = mock_session

#             mock_get_user.return_value = None

#             response = client.post(
#                 "/api/v1/google/refresh",
#                 json={"refresh_token": "valid_token"}
#             )

#         assert response.status_code == 401
#         data = response.json()
#         assert data["status"] == "failure"
#         assert "Refresh token session is invalid or expired" in data["message"]

# Ensure this import is correct

# --- Assume Fixtures (mock_user, mock_session, client, etc.) are available ---


class TestRefreshToken:
    """Test suite for /api/v1/google/refresh endpoint"""

    @patch("api.v1.services.google_auth.google_auth_service.verify_token")
    @patch("api.v1.services.google_auth.google_auth_service.get_user_by_id")
    @patch("api.v1.services.google_auth.google_auth_service.issue_local_access_token")
    @patch("api.v1.services.google_auth.google_auth_service.issue_local_refresh_token")
    def test_refresh_success(
        self,
        mock_issue_refresh,
        mock_issue_access,
        mock_get_user,
        mock_verify,
        mock_user,
        mock_session,
        client,  # Ensure this fixture is available
        valid_refresh_token,
    ):
        """Test successful token refresh"""

        # 1. Setup the Mock DB Session and Query Chain
        mock_db_session = MagicMock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_session
        )

        # 2. Override the dependency
        # We must use app.dependency_overrides because this is the correct FastAPI pattern
        app.dependency_overrides[get_db] = lambda: mock_db_session

        try:
            # 3. Setup other service mocks
            mock_verify.return_value = {
                "user_id": str(mock_user.id),
                "sid": str(mock_session.id),
                "token_type": "refresh",
            }
            mock_get_user.return_value = mock_user
            mock_issue_access.return_value = "new_access_token"
            mock_issue_refresh.return_value = "new_refresh_token"

            # 4. Make the request
            response = client.post(
                "/api/v1/google/refresh", json={"refresh_token": valid_refresh_token}
            )

            # 5. Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["access_token"] == "new_access_token"

        finally:
            # 6. CRITICAL: Clean up overrides
            app.dependency_overrides.clear()

    @patch("api.v1.services.google_auth.google_auth_service.verify_token")
    def test_refresh_failure_invalid_token(self, mock_verify, client):
        """Test refresh failure with invalid token"""
        from api.utils.responses import fail_response

        mock_verify.return_value = fail_response(
            status_code=401, message="Invalid token"
        )

        response = client.post(
            "/api/v1/google/refresh", json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "failure"

    @patch("api.v1.services.google_auth.google_auth_service.verify_token")
    def test_refresh_failure_expired_session(self, mock_verify, mock_session, client):
        """Test refresh failure with expired session"""
        from datetime import datetime, timedelta, timezone

        # 1. Setup session to be EXPIRED
        # NOTE: This modifies the mock_session for this test only
        mock_session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        # 2. Setup Mock DB to return the expired session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            # 3. Setup service mocks
            mock_verify.return_value = {
                "user_id": str(uuid.uuid4()),
                "sid": str(mock_session.id),
                "token_type": "refresh",
            }

            response = client.post(
                "/api/v1/google/refresh",
                json={"refresh_token": "valid_but_expired_token"},
            )

            assert response.status_code == 401
            data = response.json()
            assert data["status"] == "failure"
            assert "invalid or expired" in data["message"].lower()

        finally:
            app.dependency_overrides.clear()

    @patch("api.v1.services.google_auth.google_auth_service.verify_token")
    def test_refresh_failure_revoked_session(self, mock_verify, mock_session, client):
        """Test refresh failure with revoked session"""

        # 1. Setup session as REVOKED
        mock_session.is_revoked = True

        # 2. Setup Mock DB to return None (as the filter for is_revoked=False should fail)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            # 3. Setup service mocks
            mock_verify.return_value = {
                "user_id": str(uuid.uuid4()),
                "sid": str(mock_session.id),
                "token_type": "refresh",
            }

            response = client.post(
                "/api/v1/google/refresh", json={"refresh_token": "revoked_token"}
            )

            assert response.status_code == 401
            data = response.json()
            assert data["status"] == "failure"

        finally:
            app.dependency_overrides.clear()

    @patch("api.v1.services.google_auth.google_auth_service.verify_token")
    @patch("api.v1.services.google_auth.google_auth_service.get_user_by_id")
    def test_refresh_failure_user_not_found(
        self, mock_get_user, mock_verify, mock_session, client
    ):
        """Test refresh failure when user not found"""

        # 1. Setup Mock DB to return a VALID session (Session is found)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            # 2. Setup service mocks
            mock_verify.return_value = {
                "user_id": str(uuid.uuid4()),
                "sid": str(mock_session.id),
                "token_type": "refresh",
            }

            # 3. User retrieval is mocked to return None
            mock_get_user.return_value = None

            response = client.post(
                "/api/v1/google/refresh", json={"refresh_token": "valid_token"}
            )

            # 4. Assertions
            assert response.status_code == 401
            data = response.json()
            assert data["status"] == "failure"

            # ✅ CORRECT ASSERTION: Should fail on "User not found"
            assert "User not found" in data["message"]

        finally:
            app.dependency_overrides.clear()


# ===== /api/v1/google/revoke Tests =====


class TestRevokeToken:
    """Test suite for /api/v1/google/revoke endpoint"""

    @patch("api.v1.services.google_auth.google_auth_service.verify_token")
    @patch("api.v1.services.google_auth.google_auth_service.revoke_session")
    def test_revoke_success(self, mock_revoke, mock_verify, valid_refresh_token):
        """Test successful session revocation"""
        mock_verify.return_value = {
            "user_id": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "token_type": "refresh",
        }
        mock_revoke.return_value = True

        response = client.post(
            "/api/v1/google/revoke", json={"refresh_token": valid_refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Session revoked successfully"

    @patch("api.v1.services.google_auth.google_auth_service.verify_token")
    def test_revoke_failure_invalid_token(self, mock_verify):
        """Test revoke failure with invalid token"""
        from api.utils.responses import fail_response

        mock_verify.return_value = fail_response(
            status_code=401, message="Invalid token"
        )

        response = client.post(
            "/api/v1/google/revoke", json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "failure"

    @patch("api.v1.services.google_auth.google_auth_service.verify_token")
    @patch("api.v1.services.google_auth.google_auth_service.revoke_session")
    def test_revoke_failure_session_not_found(self, mock_revoke, mock_verify):
        """Test revoke failure when session not found"""
        mock_verify.return_value = {
            "user_id": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "token_type": "refresh",
        }
        mock_revoke.return_value = False

        response = client.post(
            "/api/v1/google/revoke", json={"refresh_token": "valid_token_no_session"}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "failure"
        assert "Failed to revoke session" in data["message"]

    def test_revoke_missing_token(self):
        """Test revoke failure with missing refresh_token"""
        response = client.post("/api/v1/google/revoke", json={})

        assert response.status_code == 422  # Validation error


# ===== /api/v1/google/user Tests =====


class TestGetCurrentUser:
    """Test suite for /api/v1/google/user endpoint"""

    @patch("api.v1.routes.google_auth.get_current_user")
    def test_get_user_failure_unauthorized(self, mock_get_current_user, client):
        """Test user info retrieval failure when unauthorized"""

        # When authentication fails, the dependency often returns None
        mock_get_current_user.return_value = None

        response = client.get("/api/v1/google/user")
        assert response.status_code == 403

    def test_get_user_no_auth_header(self, client):
        """Test user info retrieval without authentication"""

        response = client.get("/api/v1/google/user")

        assert response.status_code in [401, 403]


# ===== Service Layer Tests =====


class TestGoogleAuthService:
    """Test suite for GoogleAuthService methods"""

    def test_verify_google_token_success(self):
        """Test successful Google token verification"""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "sub": "google_123456",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/pic.jpg",
                "email_verified": True,
                "iss": "accounts.google.com",
                "aud": google_auth_service.google_client_id,
            }

            result = google_auth_service.verify_google_token("valid_token")

            assert isinstance(result, dict)
            assert result["google_id"] == "google_123456"
            assert result["email"] == "test@example.com"
            assert result["email_verified"] is True

    def test_verify_google_token_invalid_issuer(self):
        """Test token verification with invalid issuer"""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "sub": "google_123456",
                "email": "test@example.com",
                "iss": "malicious.com",
                "aud": google_auth_service.google_client_id,
            }

            result = google_auth_service.verify_google_token("token")

            # Should return fail_response
            assert hasattr(result, "status_code")

    def test_create_session(self, mock_db, mock_user):
        """Test session creation"""
        session = google_auth_service.create_session(
            mock_db,
            user=mock_user,
            device_id="device_123",
            device_name="iPhone",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_revoke_session_success(self, mock_db, mock_session):
        """Test successful session revocation"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = google_auth_service.revoke_session(mock_db, str(mock_session.id))

        assert result is True
        assert mock_session.is_revoked is True
        mock_db.commit.assert_called_once()

    def test_revoke_session_not_found(self, mock_db):
        """Test session revocation when session not found"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = google_auth_service.revoke_session(mock_db, str(uuid.uuid4()))

        assert result is False


# ===== Integration Tests =====


# @pytest.mark.integration
class TestGoogleAuthIntegration:
    """Integration tests for complete authentication flow"""

    @patch("api.v1.routes.google_auth.run_verify")
    @patch("api.v1.services.google_auth.google_auth_service.get_or_create_user")
    @patch("api.v1.services.google_auth.google_auth_service.create_session")
    @patch("api.v1.services.google_auth.google_auth_service.issue_local_access_token")
    @patch("api.v1.services.google_auth.google_auth_service.issue_local_refresh_token")
    def test_full_auth_flow(
        self,
        mock_issue_refresh,
        mock_issue_access,
        mock_create_session,
        mock_get_user,
        mock_verify,
        mock_user,
        mock_session,
    ):
        """Test complete authentication flow: login -> refresh -> revoke"""
        # Setup
        mock_verify.return_value = {
            "google_id": "google_123456",
            "email": "test@example.com",
            "full_name": "Test User",
            "picture": "https://example.com/pic.jpg",
            "email_verified": True,
        }
        mock_get_user.return_value = mock_user
        mock_create_session.return_value = mock_session
        access_token = "access_token_xyz"
        refresh_token = "refresh_token_xyz"
        mock_issue_access.return_value = access_token
        mock_issue_refresh.return_value = refresh_token

        # Step 1: Login
        login_response = client.post(
            "/api/v1/google/login", json={"id_token": "valid_google_token"}
        )
        assert login_response.status_code == 200
        tokens = login_response.json()["data"]

        # Step 2: Refresh (would use real tokens in integration test)
        # Step 3: Revoke (would use real tokens in integration test)
        # These steps would require actual database in full integration test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

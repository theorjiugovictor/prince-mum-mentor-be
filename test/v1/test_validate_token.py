"""
JWT Token Validation API Tests
Tests for GET /auth/validate-token endpoint
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
from api.utils.deps import get_current_user
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


# Test user ID
TEST_USER_ID = uuid.uuid4()


app.dependency_overrides[get_db] = override_get_db

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
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


class TestValidateToken:
    """Test cases for JWT token validation endpoint"""

    def test_validate_token_success(self):
        """Test validating a valid JWT token"""
        # Create a valid access token
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Token is valid"
        assert data["data"]["valid"] is True

    def test_validate_token_no_token(self):
        """Test validation without providing a token"""
        response = client.get("/api/v1/auth/validate-token")

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Could not validate credentials"

    def test_validate_token_invalid_format(self):
        """Test validation with invalid token format"""
        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": "Bearer invalid-token-format"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Could not validate credentials"

    def test_validate_token_malformed_jwt(self):
        """Test validation with malformed JWT"""
        response = client.get(
            "/api/v1/auth/validate-token",
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Could not validate credentials"

    def test_validate_token_expired_token(self):
        """Test validation with expired JWT token"""
        from jose import jwt
        import os
        from datetime import timedelta

        # Create an expired token
        SECRET_KEY = os.getenv("SECRET_KEY")
        ALGORITHM = os.getenv("ALGORITHM", "HS256")

        expired_payload = {
            "user": {"user_id": str(TEST_USER_ID), "role": "user"},
            "exp": datetime.now(timezone.utc)
            - timedelta(hours=1),  # Expired 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Could not validate credentials"

    def test_validate_token_wrong_secret(self):
        """Test validation with token signed with wrong secret"""
        from jose import jwt

        # Create token with wrong secret
        wrong_payload = {
            "user": {"user_id": str(TEST_USER_ID), "role": "user"},
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        }
        wrong_token = jwt.encode(wrong_payload, "wrong-secret-key", algorithm="HS256")

        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {wrong_token}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Could not validate credentials"

    def test_validate_token_missing_bearer(self):
        """Test validation with missing 'Bearer' prefix"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": access_token},  # Missing 'Bearer'
        )

        assert response.status_code == 401

    def test_validate_token_empty_authorization(self):
        """Test validation with empty Authorization header"""
        response = client.get(
            "/api/v1/auth/validate-token", headers={"Authorization": ""}
        )

        assert response.status_code == 401

    def test_validate_token_user_not_found(self):
        """Test validation with valid token but user doesn't exist in DB"""
        # Create token for non-existent user
        non_existent_user_id = uuid.uuid4()
        access_token = create_access_token(non_existent_user_id, "user")

        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Could not validate credentials"

    def test_validate_token_missing_user_payload(self):
        """Test validation with token missing user payload"""
        from jose import jwt
        import os

        SECRET_KEY = os.getenv("SECRET_KEY")
        ALGORITHM = os.getenv("ALGORITHM", "HS256")

        # Create token without user data
        invalid_payload = {"exp": datetime.now(timezone.utc).timestamp() + 3600}
        invalid_token = jwt.encode(invalid_payload, SECRET_KEY, algorithm=ALGORITHM)

        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Could not validate credentials"

    def test_validate_token_response_format(self):
        """Test that response has correct format"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "status" in data
        assert "status_code" in data
        assert "message" in data
        assert "data" in data

        # Check data structure
        assert "valid" in data["data"]
        assert isinstance(data["data"]["valid"], bool)
        assert data["data"]["valid"] is True

    def test_validate_token_no_user_data_exposure(self):
        """Test that response doesn't expose user data"""
        access_token = create_access_token(TEST_USER_ID, "user")

        response = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "user_id" not in data["data"]
        assert "email" not in data["data"]
        assert "full_name" not in data["data"]
        assert "phone" not in data["data"]

        # Only 'valid' should be present
        assert len(data["data"]) == 1
        assert "valid" in data["data"]

    def test_validate_token_multiple_requests(self):
        """Test multiple validation requests with same token"""
        access_token = create_access_token(TEST_USER_ID, "user")

        # First request
        response1 = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Second request
        response2 = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Third request
        response3 = client.get(
            "/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        # All should return valid
        assert response1.json()["data"]["valid"] is True
        assert response2.json()["data"]["valid"] is True
        assert response3.json()["data"]["valid"] is True

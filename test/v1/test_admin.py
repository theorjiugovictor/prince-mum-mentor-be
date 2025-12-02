import pytest

from fastapi import status
from fastapi.testclient import TestClient
from api.v1.models.user.user import User
from api.utils.security import hash_password


@pytest.fixture
def super_admin_user(db_session):
    """Create a super admin user for testing."""
    user = User(
        full_name="Super Admin",
        email="superadmin@example.com",
        phone="+2348012345678",
        password_hash=hash_password("SuperAdmin123!"),
        role="super_admin",
        email_verified=True,
        phone_verified=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session):
    """Create a regular user for testing."""
    user = User(
        full_name="Regular User",
        email="regular@example.com",
        phone="+2348012345679",
        password_hash=hash_password("RegularUser123!"),
        role="user",
        email_verified=True,
        phone_verified=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def mock_super_admin_auth(super_admin_user):
    """Mock authentication to return super admin user."""
    from main import app
    from api.utils.deps import get_current_user

    def override_get_current_user():
        return super_admin_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_regular_user_auth(regular_user):
    """Mock authentication to return regular user."""
    from main import app
    from api.utils.deps import get_current_user

    def override_get_current_user():
        return regular_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


class TestAdminRegistration:
    """Test cases for admin registration."""

    def test_successful_admin_registration_by_super_admin(
        self, client: TestClient, mock_super_admin_auth
    ):
        """Test successful admin registration by super admin."""
        admin_data = {
            "full_name": "New Admin",
            "email": "newadmin@example.com",
            "phone": "+2348123456789",
            "password": "AdminPass123!",
            "role": "admin",
        }

        response = client.post("/api/v1/admin/register", json=admin_data)

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["status"] == "success"
        assert (
            "admin" in data["message"].lower() or "created" in data["message"].lower()
        )
        assert "data" in data

        admin_user = data["data"]["admin"]
        assert admin_user["full_name"] == admin_data["full_name"]
        assert admin_user["email"] == admin_data["email"]
        assert admin_user["phone"] == admin_data["phone"]
        assert admin_user["role"] == "admin"
        assert admin_user["is_active"] is True
        assert "id" in admin_user
        assert "password" not in admin_user

    def test_admin_registration_without_authentication(self, client: TestClient):
        """Test admin registration without authentication fails."""
        admin_data = {
            "full_name": "New Admin",
            "email": "newadmin@example.com",
            "phone": "+2348123456789",
            "password": "AdminPass123!",
            "role": "admin",
        }

        response = client.post("/api/v1/admin/register", json=admin_data)

        # HTTPBearer returns 403 when no credentials provided
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_registration_by_regular_user_fails(
        self, client: TestClient, mock_regular_user_auth
    ):
        """Test admin registration by regular user fails with 403."""
        admin_data = {
            "full_name": "New Admin",
            "email": "newadmin@example.com",
            "phone": "+2348123456789",
            "password": "AdminPass123!",
            "role": "admin",
        }

        response = client.post("/api/v1/admin/register", json=admin_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_registration_with_duplicate_email(
        self, client: TestClient, mock_super_admin_auth, db_session
    ):
        """Test admin registration with duplicate email fails."""
        # Create first admin
        admin_data = {
            "full_name": "First Admin",
            "email": "duplicate@example.com",
            "phone": "+2348123456789",
            "password": "AdminPass123!",
            "role": "admin",
        }

        response1 = client.post("/api/v1/admin/register", json=admin_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create second admin with same email
        admin_data2 = admin_data.copy()
        admin_data2["phone"] = "+2348123456790"

        response2 = client.post("/api/v1/admin/register", json=admin_data2)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

        data = response2.json()
        assert "email" in data["message"].lower()

    def test_admin_registration_with_duplicate_phone(
        self, client: TestClient, mock_super_admin_auth
    ):
        """Test admin registration with duplicate phone fails."""
        # Create first admin
        admin_data = {
            "full_name": "First Admin",
            "email": "admin1@example.com",
            "phone": "+2348123456789",
            "password": "AdminPass123!",
            "role": "admin",
        }

        response1 = client.post("/api/v1/admin/register", json=admin_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create second admin with same phone
        admin_data2 = admin_data.copy()
        admin_data2["email"] = "admin2@example.com"

        response2 = client.post("/api/v1/admin/register", json=admin_data2)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

        data = response2.json()
        assert "phone" in data["message"].lower()

    def test_admin_registration_with_weak_password(
        self, client: TestClient, mock_super_admin_auth
    ):
        """Test admin registration with weak password fails."""
        weak_passwords = [
            "short",
            "nouppercase123!",
            "NOLOWERCASE123!",
            "NoDigits!",
            "NoSpecial123",
        ]

        for weak_password in weak_passwords:
            admin_data = {
                "full_name": "New Admin",
                "email": f"admin_{weak_password}@example.com",
                "phone": "+2348123456789",
                "password": weak_password,
                "role": "admin",
            }

            response = client.post("/api/v1/admin/register", json=admin_data)
            assert response.status_code in [
                422,  # HTTP_422_UNPROCESSABLE_ENTITY
                status.HTTP_400_BAD_REQUEST,
            ]

    def test_cannot_create_super_admin_via_endpoint(
        self, client: TestClient, mock_super_admin_auth
    ):
        """Test that super_admin role cannot be created via this endpoint."""
        admin_data = {
            "full_name": "Attempted Super Admin",
            "email": "superadmin2@example.com",
            "phone": "+2348123456789",
            "password": "SuperAdmin123!",
            "role": "super_admin",
        }

        response = client.post("/api/v1/admin/register", json=admin_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "super_admin" in data["message"].lower()

    def test_admin_registration_with_missing_fields(
        self, client: TestClient, mock_super_admin_auth
    ):
        """Test admin registration with missing required fields fails."""
        required_fields = ["full_name", "email", "password"]

        for field in required_fields:
            incomplete_data = {
                "full_name": "New Admin",
                "email": "admin@example.com",
                "password": "AdminPass123!",
                "role": "admin",
            }
            del incomplete_data[field]

            response = client.post("/api/v1/admin/register", json=incomplete_data)
            assert response.status_code == 422  # HTTP_422_UNPROCESSABLE_ENTITY

    def test_admin_registration_with_invalid_email(
        self, client: TestClient, mock_super_admin_auth
    ):
        """Test admin registration with invalid email format fails."""
        admin_data = {
            "full_name": "New Admin",
            "email": "invalid-email",
            "phone": "+2348123456789",
            "password": "AdminPass123!",
            "role": "admin",
        }

        response = client.post("/api/v1/admin/register", json=admin_data)
        assert response.status_code == 422  # HTTP_422_UNPROCESSABLE_ENTITY

    def test_admin_registration_response_structure(
        self, client: TestClient, mock_super_admin_auth
    ):
        """Test that admin registration response has correct structure."""
        admin_data = {
            "full_name": "New Admin",
            "email": "structuretest@example.com",
            "phone": "+2348123456789",
            "password": "AdminPass123!",
            "role": "admin",
        }

        response = client.post("/api/v1/admin/register", json=admin_data)

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()

        # Check top-level structure
        assert "status" in data
        assert "status_code" in data
        assert "message" in data
        assert "data" in data

        # Check admin data structure
        admin_user = data["data"]["admin"]
        required_fields = ["id", "full_name", "email", "role", "is_active"]
        for field in required_fields:
            assert field in admin_user

        # Ensure sensitive data is not exposed
        assert "password" not in admin_user
        assert "password_hash" not in admin_user

    def test_admin_registration_without_phone(
        self, client: TestClient, mock_super_admin_auth
    ):
        """Test admin registration without phone number succeeds."""
        admin_data = {
            "full_name": "Admin No Phone",
            "email": "nophone@example.com",
            "password": "AdminPass123!",
            "role": "admin",
        }

        response = client.post("/api/v1/admin/register", json=admin_data)

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        admin_user = data["data"]["admin"]
        assert admin_user["phone"] is None

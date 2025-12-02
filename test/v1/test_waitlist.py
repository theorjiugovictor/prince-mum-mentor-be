import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime
import uuid


class TestWaitlist:
    """
    Test suite for waitlist endpoint

    Required Tests:
    1. Success case (201)
    2. Validation error (422)
    3. Server error (500)
    """

    # TEST 1: SUCCESS CASE (201)

    def test_join_waitlist_success_returns_201(self, client, mock_send_email):
        """
        Test successful waitlist registration with valid data.

        Expected behavior:
        - Returns 201 status code
        - Returns success message
        - Returns user data with id, full_name, email, joined_at
        - Sends welcome email
        """
        payload = {"full_name": "Jane Doe", "email": "jane.doe@example.com"}

        response = client.post("/api/v1/waitlist", json=payload)

        # Assert status code
        assert response.status_code == 201

        # Assert response structure
        data = response.json()
        assert "message" in data
        assert "data" in data
        assert data["message"] == "Successfully joined the waitlist"

        # Assert data fields
        assert data["data"]["full_name"] == "Jane Doe"
        assert data["data"]["email"] == "jane.doe@example.com"
        assert "id" in data["data"]
        assert "joined_at" in data["data"]

        # Validate UUID format
        try:
            uuid.UUID(data["data"]["id"])
        except ValueError:
            pytest.fail("Invalid UUID format")

        # Validate datetime format
        try:
            datetime.fromisoformat(data["data"]["joined_at"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Invalid datetime format")

        # Assert email was sent
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert call_args[0][0] == "jane.doe@example.com"
        assert call_args[0][1] == "Welcome to Mum Mentor Waitlist!"
        assert "Hi Jane Doe" in call_args[0][2]

    # TEST 2: VALIDATION ERROR (422)

    def test_join_waitlist_invalid_email_returns_422(self, client):
        """
        Test validation error when email format is invalid.

        Expected behavior:
        - Returns 422 status code
        - Returns validation error details
        - Does not create waitlist entry
        """
        payload = {
            "full_name": "Jane Doe",
            "email": "invalid-email-format",  # Invalid email
        }

        response = client.post("/api/v1/waitlist", json=payload)

        # Assert status code
        assert response.status_code == 422

        # Assert error details present
        data = response.json()
        assert "detail" in data

    def test_join_waitlist_empty_name_returns_422(self, client):
        """
        Test validation error when full_name is empty or whitespace.

        Expected behavior:
        - Returns 422 status code
        - Returns validation error
        """
        payload = {
            "full_name": "   ",  # Empty/whitespace only
            "email": "jane@example.com",
        }

        response = client.post("/api/v1/waitlist", json=payload)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_join_waitlist_missing_required_fields_returns_422(self, client):
        """
        Test validation error when required fields are missing.

        Expected behavior:
        - Returns 422 for missing full_name
        - Returns 422 for missing email
        """
        # Test missing full_name
        response = client.post("/api/v1/waitlist", json={"email": "jane@example.com"})
        assert response.status_code == 422

        # Test missing email
        response = client.post("/api/v1/waitlist", json={"full_name": "Jane Doe"})
        assert response.status_code == 422

        # Test missing both
        response = client.post("/api/v1/waitlist", json={})
        assert response.status_code == 422

    def test_join_waitlist_name_too_long_returns_422(self, client):
        """
        Test validation error when name exceeds maximum length.

        Expected behavior:
        - Returns 422 status code when name > 100 characters
        """
        payload = {
            "full_name": "A" * 101,  # Exceeds 100 character limit
            "email": "jane@example.com",
        }

        response = client.post("/api/v1/waitlist", json=payload)

        assert response.status_code == 422

    # TEST 3: SERVER ERROR (500)

    def test_join_waitlist_database_error_returns_500(self, client, db_session):
        """
        Test internal server error when database operation fails.

        Expected behavior:
        - Returns 500 status code
        - Returns error message
        - Handles database failure gracefully
        """
        payload = {"full_name": "Jane Doe", "email": "jane@example.com"}

        # Mock database service to raise an exception
        with patch("api.v1.routes.waitlist.create_waitlist_entry") as mock_service:
            # Simulate database failure
            mock_service.return_value = (None, None)

            response = client.post("/api/v1/waitlist", json=payload)

            # Assert status code
            assert response.status_code == 500

            # Assert error response
            data = response.json()
            assert "message" in data
            assert data["message"] == "Failed to create waitlist entry"

    def test_join_waitlist_duplicate_email_returns_200(self, client, mock_send_email):
        """
        Test handling of duplicate email registration.

        Expected behavior:
        - First registration succeeds (201)
        - Second registration returns existing entry (200)
        - Email only sent once
        """
        payload = {"full_name": "Jane Doe", "email": "jane@example.com"}

        # First registration
        response1 = client.post("/api/v1/waitlist", json=payload)
        assert response1.status_code == 201

        # Duplicate registration
        response2 = client.post("/api/v1/waitlist", json=payload)
        assert response2.status_code == 200

        data = response2.json()
        assert data["message"] == "Email already registered on waitlist"
        assert data["data"]["email"] == "jane@example.com"

        # Verify email only sent once
        assert mock_send_email.call_count == 1

    def test_join_waitlist_email_normalization(self, client, mock_send_email):
        """
        Test email normalization (lowercase, trimmed).

        Expected behavior:
        - Email is converted to lowercase
        - Whitespace is trimmed
        """
        payload = {"full_name": "Jane Doe", "email": "  Jane.Doe@EXAMPLE.COM  "}

        response = client.post("/api/v1/waitlist", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["email"] == "jane.doe@example.com"

    def test_join_waitlist_name_trimming(self, client, mock_send_email):
        """
        Test full_name trimming removes leading/trailing whitespace.

        Expected behavior:
        - Whitespace is trimmed from full_name
        """
        payload = {"full_name": "  Jane Doe  ", "email": "jane@example.com"}

        response = client.post("/api/v1/waitlist", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["full_name"] == "Jane Doe"

    def test_join_waitlist_case_insensitive_duplicate(self, client, mock_send_email):
        """
        Test duplicate detection is case-insensitive.

        Expected behavior:
        - jane@example.com and JANE@EXAMPLE.COM treated as duplicates
        """
        payload1 = {"full_name": "Jane Doe", "email": "jane@example.com"}
        payload2 = {"full_name": "Jane Smith", "email": "JANE@EXAMPLE.COM"}

        response1 = client.post("/api/v1/waitlist", json=payload1)
        assert response1.status_code == 201

        response2 = client.post("/api/v1/waitlist", json=payload2)
        assert response2.status_code == 200
        assert response2.json()["message"] == "Email already registered on waitlist"

    def test_join_waitlist_special_characters_in_name(self, client, mock_send_email):
        """
        Test names with special characters are handled correctly.

        Expected behavior:
        - Special characters preserved
        - Accents, hyphens, apostrophes accepted
        """
        payload = {"full_name": "María O'Brien-Smith", "email": "maria@example.com"}

        response = client.post("/api/v1/waitlist", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["full_name"] == "María O'Brien-Smith"

    def test_join_waitlist_multiple_users(self, client, mock_send_email):
        """
        Test multiple unique users can join successfully.

        Expected behavior:
        - Each unique email creates new entry
        - All registrations succeed
        """
        users = [
            {"full_name": "Jane Doe", "email": "jane@example.com"},
            {"full_name": "John Smith", "email": "john@example.com"},
            {"full_name": "Alice Brown", "email": "alice@example.com"},
        ]

        for user in users:
            response = client.post("/api/v1/waitlist", json=user)
            assert response.status_code == 201

        # Verify all emails were sent
        assert mock_send_email.call_count == 3


class TestWaitlistDelete:
    """
    Test suite for waitlist deletion endpoint (admin only)
    """

    def test_delete_waitlist_user_success_returns_200(self, client, db):
        """
        Test successful deletion of a waitlist user by admin.

        Expected behavior:
        - Returns 200 status code
        - Returns success message
        - Returns deleted user data
        - User is removed from database
        """
        from api.v1.models.user.user import Waitlist, User
        from api.utils.auth_utils import create_access_token

        # Create a waitlist entry
        waitlist_entry = Waitlist(full_name="Test User", email="test@example.com")
        db.add(waitlist_entry)
        db.commit()
        db.refresh(waitlist_entry)

        # Create admin user
        admin_user = User(
            id=uuid.uuid4(),
            full_name="Admin User",
            email="admin@example.com",
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()

        # Generate admin token
        admin_token = create_access_token(admin_user.id, "admin")

        # Delete the waitlist entry
        response = client.delete(
            f"/api/v1/waitlist/{waitlist_entry.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert status code
        assert response.status_code == 200

        # Assert response structure
        data = response.json()
        assert data["message"] == "Waitlist entry deleted successfully"
        assert data["data"]["id"] == str(waitlist_entry.id)
        assert data["data"]["full_name"] == "Test User"
        assert data["data"]["email"] == "test@example.com"

        # Verify entry is deleted from database
        deleted_entry = (
            db.query(Waitlist).filter(Waitlist.id == waitlist_entry.id).first()
        )
        assert deleted_entry is None

    def test_delete_waitlist_user_not_found_returns_404(self, client, db):
        """
        Test deletion of non-existent waitlist entry.

        Expected behavior:
        - Returns 404 status code
        - Returns error message
        """
        from api.v1.models.user.user import User
        from api.utils.auth_utils import create_access_token

        # Create admin user
        admin_user = User(
            id=uuid.uuid4(),
            full_name="Admin User",
            email="admin@example.com",
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()

        # Generate admin token
        admin_token = create_access_token(admin_user.id, "admin")

        # Try to delete non-existent entry
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/waitlist/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert status code
        assert response.status_code == 404

        # Assert error message
        data = response.json()
        assert data["message"] == "Waitlist entry not found"

    def test_delete_waitlist_invalid_id_format_returns_400(self, client, db):
        """
        Test deletion with invalid UUID format.

        Expected behavior:
        - Returns 400 status code
        - Returns validation error message
        """
        from api.v1.models.user.user import User
        from api.utils.auth_utils import create_access_token

        # Create admin user
        admin_user = User(
            id=uuid.uuid4(),
            full_name="Admin User",
            email="admin@example.com",
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()

        # Generate admin token
        admin_token = create_access_token(admin_user.id, "admin")

        # Try to delete with invalid ID format
        response = client.delete(
            "/api/v1/waitlist/invalid-id-format",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert status code
        assert response.status_code == 400

        # Assert error message
        data = response.json()
        assert data["message"] == "Invalid waitlist ID format"

    def test_delete_waitlist_non_admin_returns_403(self, client, db):
        """
        Test deletion attempt by non-admin user.

        Expected behavior:
        - Returns 403 status code
        - Rejects access
        """
        from api.v1.models.user.user import Waitlist, User
        from api.utils.auth_utils import create_access_token

        # Create a waitlist entry
        waitlist_entry = Waitlist(full_name="Test User", email="test@example.com")
        db.add(waitlist_entry)
        db.commit()
        db.refresh(waitlist_entry)

        # Create regular (non-admin) user
        regular_user = User(
            id=uuid.uuid4(),
            full_name="Regular User",
            email="regular@example.com",
            role="user",
            is_active=True,
        )
        db.add(regular_user)
        db.commit()

        # Generate regular user token
        user_token = create_access_token(regular_user.id, "user")

        # Try to delete as non-admin
        response = client.delete(
            f"/api/v1/waitlist/{waitlist_entry.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        # Assert status code
        assert response.status_code == 403

        # Assert error message
        data = response.json()
        assert data["detail"] == "Admin access required"

    def test_delete_waitlist_unauthorized_returns_401(self, client, db):
        """
        Test deletion attempt without authentication.

        Expected behavior:
        - Returns 401 status code
        - Rejects access
        """
        from api.v1.models.user.user import Waitlist

        # Create a waitlist entry
        waitlist_entry = Waitlist(full_name="Test User", email="test@example.com")
        db.add(waitlist_entry)
        db.commit()
        db.refresh(waitlist_entry)

        # Try to delete without authentication
        response = client.delete(f"/api/v1/waitlist/{waitlist_entry.id}")

        # Assert status code
        assert response.status_code == 403  # HTTPBearer returns 403 when no credentials

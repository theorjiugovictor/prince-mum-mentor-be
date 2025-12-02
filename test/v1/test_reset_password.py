import pytest
from fastapi import status
from fastapi import HTTPException

from api.v1.schemas.reset_password import ResetPassword
from api.v1.services.reset_password import reset_password_service
from api.utils.security import verify_password


# Successful Response Tests (2xx)
class TestResetPasswordSuccess:
    """Test successful password reset scenarios (20x status codes)"""

    def test_successful_password_reset_via_service(self, db_session, test_user):
        """Test successful password reset through service layer"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        result = reset_password_service(db_session, data, str(test_user.id))

        assert result is None
        db_session.refresh(test_user)
        assert verify_password("NewPassword123", test_user.password_hash)
        assert not verify_password("OldPassword123", test_user.password_hash)

    def test_successful_password_reset_via_endpoint(
        self, client, test_user, monkeypatch
    ):
        """Test successful password reset through API endpoint"""
        from api.v1.routes import reset_password as reset_password_module

        original_endpoint = reset_password_module.reset_password

        async def mock_reset_password(request, db):
            reset_password_service(db, request, str(test_user.id))
            from api.utils.responses import success_response

            return success_response(
                status_code=status.HTTP_200_OK, message="Password reset successfully"
            )

        monkeypatch.setattr(
            reset_password_module, "reset_password", mock_reset_password
        )

        response = client.patch(
            "/api/v1/reset-password",
            json={
                "old_password": "OldPassword123",
                "new_password": "NewPassword456",
                "confirm_password": "NewPassword456",
            },
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password reset successfully"

    def test_password_reset_with_minimum_length_password(self, db_session, test_user):
        """Test password reset with exactly 8 character password"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPass1",
            confirm_password="NewPass1",
        )

        result = reset_password_service(db_session, data, str(test_user.id))

        assert result is None
        db_session.refresh(test_user)
        assert verify_password("NewPass1", test_user.password_hash)

    def test_password_reset_with_long_password(self, db_session, test_user):
        """Test password reset with very long password"""
        long_password = "VeryLongPassword123456789012345678901234567890"
        data = ResetPassword(
            old_password="OldPassword123",
            new_password=long_password,
            confirm_password=long_password,
        )

        result = reset_password_service(db_session, data, str(test_user.id))

        assert result is None
        db_session.refresh(test_user)
        assert verify_password(long_password, test_user.password_hash)

    def test_password_reset_with_special_characters(self, db_session, test_user):
        """Test password reset with special characters"""
        special_password = "P@ssw0rd!#$%"
        data = ResetPassword(
            old_password="OldPassword123",
            new_password=special_password,
            confirm_password=special_password,
        )

        result = reset_password_service(db_session, data, str(test_user.id))

        assert result is None
        db_session.refresh(test_user)
        assert verify_password(special_password, test_user.password_hash)

    def test_password_with_leading_trailing_spaces(self, db_session, test_user):
        """Test that passwords with spaces are trimmed"""
        data = ResetPassword(
            old_password="  OldPassword123  ",
            new_password="  NewPassword123  ",
            confirm_password="  NewPassword123  ",
        )

        result = reset_password_service(db_session, data, str(test_user.id))

        assert result is None
        db_session.refresh(test_user)
        # Passwords should be trimmed
        assert verify_password("NewPassword123", test_user.password_hash)

    def test_unicode_characters_in_password(self, db_session, test_user):
        """Test password with unicode characters"""
        unicode_password = "Pässwörd123"
        data = ResetPassword(
            old_password="OldPassword123",
            new_password=unicode_password,
            confirm_password=unicode_password,
        )

        result = reset_password_service(db_session, data, str(test_user.id))

        assert result is None
        db_session.refresh(test_user)
        assert verify_password(unicode_password, test_user.password_hash)


# Input Validation Tests (4xx)
class TestResetPasswordValidationErrors:
    """Test input validation errors (40x status codes)"""

    # Schema validation tests (400)
    def test_empty_old_password(self):
        """Test validation fails when old password is empty"""
        with pytest.raises(ValueError, match="Old password field cannot be empty"):
            ResetPassword(
                old_password="",
                new_password="NewPassword123",
                confirm_password="NewPassword123",
            )

    def test_empty_new_password(self):
        """Test validation fails when new password is empty"""
        with pytest.raises(ValueError, match="New password field cannot be empty"):
            ResetPassword(
                old_password="OldPassword123",
                new_password="",
                confirm_password="NewPassword123",
            )

    def test_empty_confirm_password(self):
        """Test validation fails when confirm password is empty"""
        with pytest.raises(ValueError, match="Confirm password field cannot be empty"):
            ResetPassword(
                old_password="OldPassword123",
                new_password="NewPassword123",
                confirm_password="",
            )

    def test_whitespace_only_old_password(self):
        """Test validation fails when old password is only whitespace"""
        with pytest.raises(ValueError, match="Old password field cannot be empty"):
            ResetPassword(
                old_password="   ",
                new_password="NewPassword123",
                confirm_password="NewPassword123",
            )

    def test_old_password_too_short(self):
        """Test validation fails when old password is less than 8 characters"""
        with pytest.raises(
            ValueError, match="Old password must be at least 8 characters long"
        ):
            ResetPassword(
                old_password="Short1",
                new_password="NewPassword123",
                confirm_password="NewPassword123",
            )

    def test_new_password_too_short(self):
        """Test validation fails when new password is less than 8 characters"""
        with pytest.raises(
            ValueError, match="New password must be at least 8 characters long"
        ):
            ResetPassword(
                old_password="OldPassword123",
                new_password="Short1",
                confirm_password="Short1",
            )

    def test_confirm_password_too_short(self):
        """Test validation fails when confirm password is less than 8 characters"""
        with pytest.raises(
            ValueError, match="Confirm password must be at least 8 characters long"
        ):
            ResetPassword(
                old_password="OldPassword123",
                new_password="NewPassword123",
                confirm_password="Short1",
            )

    def test_password_exactly_8_chars(self):
        """Test password with exactly 8 characters (boundary)"""
        data = ResetPassword(
            old_password="Pass1234",
            new_password="NewPass1",
            confirm_password="NewPass1",
        )
        assert data.new_password == "NewPass1"

    def test_password_7_chars_fails(self):
        """Test password with 7 characters fails validation"""
        with pytest.raises(ValueError, match="must be at least 8 characters long"):
            ResetPassword(
                old_password="Pass123",
                new_password="NewPass123",
                confirm_password="NewPass123",
            )

    def test_passwords_do_not_match(self, db_session, test_user):
        """Test service fails when new password and confirm password don't match"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="DifferentPassword123",
        )

        with pytest.raises(HTTPException) as exc_info:
            reset_password_service(db_session, data, str(test_user.id))

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "New passwords do not match"

    def test_invalid_uuid_format(self, db_session):
        """Test service fails when user_id is not a valid UUID"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        with pytest.raises(Exception):  # SQLAlchemy will raise an error
            reset_password_service(db_session, data, "invalid-uuid")

    # Authentication/Authorization tests (401)
    def test_incorrect_old_password(self, db_session, test_user):
        """Test service fails when old password is incorrect"""
        data = ResetPassword(
            old_password="WrongPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        with pytest.raises(HTTPException) as exc_info:
            reset_password_service(db_session, data, str(test_user.id))

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Old password is incorrect"

    # Resource not found tests (404)
    def test_user_not_found(self, db_session):
        """Test service fails when user does not exist"""
        import uuid

        non_existent_user_id = str(uuid.uuid4())

        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        with pytest.raises(HTTPException) as exc_info:
            reset_password_service(db_session, data, non_existent_user_id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    def test_null_user_id(self, db_session):
        """Test service fails when user_id is None"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        with pytest.raises(HTTPException) as exc_info:
            reset_password_service(db_session, data, None)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    def test_empty_string_user_id(self, db_session):
        """Test service fails when user_id is empty string"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        with pytest.raises(HTTPException) as exc_info:
            reset_password_service(db_session, data, "")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    # Edge cases
    def test_new_password_same_as_old(self, db_session, test_user):
        """Test password reset when new password is same as old (should succeed but not ideal)"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="OldPassword123",
            confirm_password="OldPassword123",
        )

        # This should technically succeed as there's no validation preventing it
        result = reset_password_service(db_session, data, str(test_user.id))
        assert result is None


# Server Failure Tests (5xx)
class TestResetPasswordServerErrors:
    """Test server error scenarios (50x status codes)"""

    def test_database_commit_failure(self, db_session, test_user, monkeypatch):
        """Test handling of database commit failure"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        def mock_commit():
            raise Exception("Database connection lost")

        monkeypatch.setattr(db_session, "commit", mock_commit)

        with pytest.raises(Exception, match="Database connection lost"):
            reset_password_service(db_session, data, str(test_user.id))

    def test_database_refresh_failure(self, db_session, test_user, monkeypatch):
        """Test handling of database refresh failure"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        def mock_refresh(obj):
            raise Exception("Failed to refresh object")

        monkeypatch.setattr(db_session, "refresh", mock_refresh)

        with pytest.raises(Exception, match="Failed to refresh object"):
            reset_password_service(db_session, data, str(test_user.id))

    def test_hash_password_failure(self, db_session, test_user, monkeypatch):
        """Test handling of password hashing failure"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        from api.v1.services import reset_password as reset_password_module

        def mock_hash_password(password):
            raise Exception("Hashing algorithm failed")

        monkeypatch.setattr(reset_password_module, "hash_password", mock_hash_password)

        with pytest.raises(Exception, match="Hashing algorithm failed"):
            reset_password_service(db_session, data, str(test_user.id))

    def test_verify_password_failure(self, db_session, test_user, monkeypatch):
        """Test handling of password verification failure"""
        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        from api.v1.services import reset_password as reset_password_module

        def mock_verify_password(plain, hashed):
            raise Exception("Verification algorithm failed")

        monkeypatch.setattr(
            reset_password_module, "verify_password", mock_verify_password
        )

        with pytest.raises(Exception, match="Verification algorithm failed"):
            reset_password_service(db_session, data, str(test_user.id))

    def test_database_query_failure(self, db_session, monkeypatch):
        """Test handling of database query failure"""
        import uuid

        data = ResetPassword(
            old_password="OldPassword123",
            new_password="NewPassword123",
            confirm_password="NewPassword123",
        )

        original_query = db_session.query

        def mock_query(*args, **kwargs):
            result = original_query(*args, **kwargs)
            original_filter = result.filter

            def mock_filter(*filter_args, **filter_kwargs):
                raise Exception("Database query timeout")

            result.filter = mock_filter
            return result

        monkeypatch.setattr(db_session, "query", mock_query)

        with pytest.raises(Exception, match="Database query timeout"):
            reset_password_service(db_session, data, str(uuid.uuid4()))

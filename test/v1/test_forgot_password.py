import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta, timezone


class TestForgotPassword:
    """
    Test suite for forgot password endpoint

    Required Tests:
    1. Success case - valid email (200)
    2. User not found (404)
    3. Inactive user account (403)
    4. Email sending failure (500)
    5. Invalid email format (422)
    """

    @pytest.fixture
    def mock_send_email(self):
        """Mock the send_email function for forgot password."""
        with patch(
            "api.v1.services.forgot_password.send_email", new_callable=AsyncMock
        ) as mock:
            mock.return_value = None
            yield mock

    def test_forgot_password_success_returns_200(
        self, client, test_user, db_session, mock_send_email
    ):
        """
        Test successful forgot password request with valid email.

        Expected behavior:
        - Returns 200 status code
        - Returns success message
        - Creates OTP record in database
        - Sends email with reset code
        - Invalidates old unused OTPs
        """
        payload = {"email": "testuser@example.com"}

        response = client.post("/api/v1/auth/forgot-password", json=payload)

        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "data" in data
        assert data["message"] == "Password reset code has been sent to your email"
        assert data["data"]["email"] == "testuser@example.com"

        # Verify email was sent
        mock_send_email.assert_called_once()

        # Verify OTP was created
        from api.v1.models.user.user import UserOTPVerification

        otp_record = (
            db_session.query(UserOTPVerification)
            .filter(
                UserOTPVerification.user_id == test_user.id,
                UserOTPVerification.otp_type == "password_reset",
                UserOTPVerification.used == False,
            )
            .first()
        )

        assert otp_record is not None
        assert len(otp_record.otp_code) == 6
        assert otp_record.otp_code.isdigit()
        assert otp_record.channel == "email"
        assert otp_record.attempts == 0
        assert otp_record.max_attempts == 3

    def test_forgot_password_user_not_found_returns_404(self, client, mock_send_email):
        """
        Test forgot password request with non-existent email.

        Expected behavior:
        - Returns 404 status code
        - Returns appropriate error message
        - Does not send email
        """
        payload = {"email": "nonexistent@example.com"}

        response = client.post("/api/v1/auth/forgot-password", json=payload)

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert data["detail"] == "User with this email does not exist"

        # Verify no email was sent
        mock_send_email.assert_not_called()

    def test_forgot_password_inactive_user_returns_403(
        self, client, test_user, db_session, mock_send_email
    ):
        """
        Test forgot password request for inactive user.

        Expected behavior:
        - Returns 403 status code
        - Returns appropriate error message
        - Does not send email
        """
        # Make user inactive
        test_user.is_active = False
        db_session.commit()

        payload = {"email": "testuser@example.com"}

        response = client.post("/api/v1/auth/forgot-password", json=payload)

        assert response.status_code == 403

        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Account is inactive. Please contact support."

        # Verify no email was sent
        mock_send_email.assert_not_called()

    def test_forgot_password_email_sending_fails_returns_500(
        self, client, test_user, mock_send_email
    ):
        """
        Test forgot password when email sending fails.

        Expected behavior:
        - Returns 500 status code
        - Returns appropriate error message
        """
        # Make send_email raise an exception
        mock_send_email.side_effect = Exception("SMTP server error")

        payload = {"email": "testuser@example.com"}

        response = client.post("/api/v1/auth/forgot-password", json=payload)

        assert response.status_code == 500

        data = response.json()
        assert "detail" in data
        assert (
            data["detail"]
            == "Failed to send password reset code. Please try again later."
        )

    def test_forgot_password_invalid_email_format_returns_422(self, client):
        """
        Test forgot password with invalid email format.

        Expected behavior:
        - Returns 422 status code
        - Returns validation error
        """
        payload = {"email": "invalid-email"}

        response = client.post("/api/v1/auth/forgot-password", json=payload)

        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_forgot_password_empty_email_returns_422(self, client):
        """
        Test forgot password with empty email.

        Expected behavior:
        - Returns 422 status code
        - Returns validation error
        """
        payload = {"email": ""}

        response = client.post("/api/v1/auth/forgot-password", json=payload)

        assert response.status_code == 422

    def test_forgot_password_case_insensitive_email(
        self, client, test_user, db_session, mock_send_email
    ):
        """
        Test forgot password with different email case.

        Expected behavior:
        - Returns 200 status code
        - Finds user regardless of email case
        - Sends reset code
        """
        payload = {"email": "TESTUSER@EXAMPLE.COM"}

        response = client.post("/api/v1/auth/forgot-password", json=payload)

        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Password reset code has been sent to your email"

        # Verify email was sent
        mock_send_email.assert_called_once()

    def test_forgot_password_invalidates_old_otps(
        self, client, test_user, db_session, mock_send_email
    ):
        """
        Test that requesting forgot password invalidates old unused OTPs.

        Expected behavior:
        - Creates new OTP
        - Marks old unused OTPs as used
        - Only one active OTP exists
        """
        from api.v1.models.user.user import UserOTPVerification

        # Create an existing OTP
        old_otp = UserOTPVerification(
            user_id=test_user.id,
            otp_code="123456",
            otp_type="password_reset",
            channel="email",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            used=False,
        )
        db_session.add(old_otp)
        db_session.commit()

        payload = {"email": "testuser@example.com"}

        response = client.post("/api/v1/auth/forgot-password", json=payload)

        assert response.status_code == 200

        # Verify old OTP is marked as used
        db_session.refresh(old_otp)
        assert old_otp.used == True
        assert old_otp.used_at is not None

        # Verify only one active OTP exists
        active_otps = (
            db_session.query(UserOTPVerification)
            .filter(
                UserOTPVerification.user_id == test_user.id,
                UserOTPVerification.otp_type == "password_reset",
                UserOTPVerification.used == False,
            )
            .all()
        )

        assert len(active_otps) == 1
        assert active_otps[0].otp_code != "123456"

    def test_forgot_password_otp_expiration_time(
        self, client, test_user, db_session, mock_send_email
    ):
        """
        Test that OTP has correct expiration time (15 minutes).

        Expected behavior:
        - OTP expires_at is ~15 minutes from creation
        """
        from api.v1.models.user.user import UserOTPVerification

        payload = {"email": "testuser@example.com"}

        before_request = datetime.now(timezone.utc)
        response = client.post("/api/v1/auth/forgot-password", json=payload)
        after_request = datetime.now(timezone.utc)

        assert response.status_code == 200

        # Get the OTP record
        otp_record = (
            db_session.query(UserOTPVerification)
            .filter(
                UserOTPVerification.user_id == test_user.id,
                UserOTPVerification.used == False,
            )
            .first()
        )

        assert otp_record is not None

        # Check expiration is approximately 15 minutes from now
        expected_expiry_min = before_request + timedelta(minutes=15)
        expected_expiry_max = after_request + timedelta(minutes=15)

        # Make otp_record.expires_at timezone-aware if it's naive
        otp_expires_at = otp_record.expires_at
        if otp_expires_at.tzinfo is None:
            otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)

        assert expected_expiry_min <= otp_expires_at <= expected_expiry_max

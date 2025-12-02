import pytest
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from api.v1.schemas.verify_otp import VerifyOTPRequest
from api.v1.services.verify_otp import VerifyOTPService
from api.v1.models.user.user import UserOTPVerification


class TestVerifyOTPService:
    def test_successful_verify_via_service(self, db_session, test_user):
        # create OTP
        otp = UserOTPVerification(
            user_id=test_user.id,
            otp_code="123456",
            otp_type="email_verification",
            channel="email",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            used=False,
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)

        data = VerifyOTPRequest(
            user_id=str(test_user.id), otp_code="123456", otp_type="email_verification"
        )
        user = VerifyOTPService(db_session, data)

        assert user.email_verified is True

    def test_incorrect_otp_increments_attempts(self, db_session, test_user):
        otp = UserOTPVerification(
            user_id=test_user.id,
            otp_code="0000",
            otp_type="email_verification",
            channel="email",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            used=False,
            attempts=0,
            max_attempts=3,
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)

        data = VerifyOTPRequest(
            user_id=str(test_user.id), otp_code="1111", otp_type="email_verification"
        )

        with pytest.raises(HTTPException) as exc:
            VerifyOTPService(db_session, data)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

        db_session.refresh(otp)
        assert otp.attempts == 1

    def test_expired_otp_raises(self, db_session, test_user):
        otp = UserOTPVerification(
            user_id=test_user.id,
            otp_code="2222",
            otp_type="email_verification",
            channel="email",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            used=False,
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)

        data = VerifyOTPRequest(
            user_id=str(test_user.id), otp_code="2222", otp_type="email_verification"
        )

        with pytest.raises(HTTPException) as exc:
            VerifyOTPService(db_session, data)

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_max_attempts_locks_otp(self, db_session, test_user):
        """Test that OTP gets locked after max attempts"""
        otp = UserOTPVerification(
            user_id=test_user.id,
            otp_code="5555",
            otp_type="email_verification",
            channel="email",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            used=False,
            attempts=0,
            max_attempts=3,
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)

        # Make 3 failed attempts
        for i in range(3):
            data = VerifyOTPRequest(
                user_id=str(test_user.id),
                otp_code="9999",
                otp_type="email_verification",
            )
            with pytest.raises(HTTPException):
                VerifyOTPService(db_session, data)
            db_session.refresh(otp)

        # Verify OTP is now locked (used=True)
        assert otp.used is True
        assert otp.attempts == 3

        # Try with correct code - should still fail because it's locked
        data = VerifyOTPRequest(
            user_id=str(test_user.id), otp_code="5555", otp_type="email_verification"
        )
        with pytest.raises(HTTPException) as exc:
            VerifyOTPService(db_session, data)

        # Should get "OTP record not found" because used=True
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    def test_endpoint_verify_otp_via_client(self, client, db_session, test_user):
        """Test the full endpoint via test client and verify JWT tokens are returned"""
        otp = UserOTPVerification(
            user_id=test_user.id,
            otp_code="3333",
            otp_type="email_verification",
            channel="email",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            used=False,
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)

        response = client.post(
            "/api/v1/verify-otp",
            json={
                "user_id": str(test_user.id),
                "otp_code": "3333",
                "otp_type": "email_verification",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "OTP verified successfully"

        # Verify JWT tokens are returned
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["access_token"] is not None
        assert data["data"]["refresh_token"] is not None
        assert len(data["data"]["access_token"]) > 0
        assert len(data["data"]["refresh_token"]) > 0

        # Verify user data is returned
        assert "user" in data["data"]
        assert data["data"]["user"]["id"] == str(test_user.id)
        assert data["data"]["user"]["email"] == test_user.email
        assert data["data"]["user"]["full_name"] == test_user.full_name
        assert (
            data["data"]["user"]["email_verified"] == True
        )  # Should be True after verification

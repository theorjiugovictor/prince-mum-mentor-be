"""Utility functions for tests"""


def create_mock_google_token_response(
    google_id="123456789",
    email="test@gmail.com",
    name="Test User",
    picture="https://example.com/pic.jpg",
    email_verified=True,
    issuer="accounts.google.com",
    audience="407408718192.apps.googleusercontent.com",
):
    """Create a mock Google token response"""
    return {
        "iss": issuer,
        "sub": google_id,
        "email": email,
        "name": name,
        "picture": picture,
        "email_verified": email_verified,
        "aud": audience,
        "exp": 9999999999,
        "iat": 1234567890,
    }


def assert_user_response(response_data, expected_email, expected_name):
    """Helper to assert user response structure"""
    assert "id" in response_data
    assert response_data["email"] == expected_email
    assert response_data["full_name"] == expected_name
    assert "is_active" in response_data
    assert "email_verified" in response_data

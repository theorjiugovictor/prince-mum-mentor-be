import sys
import os
import pytest
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["TESTING"] = "true"

from main import app
from api.db.database import get_db
from api.db.base_model import Base
from api.v1.models.user.user import User, UserProfile
from api.utils.security import hash_password

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_session):
    """Alias for db_session for convenience."""
    return db_session


@pytest.fixture
def test_user(db_session):
    """Create a test user with a hashed password."""
    user = User(
        full_name="Test User",
        email="testuser@example.com",
        phone="+2348012345678",
        password_hash=hash_password("OldPassword123"),
        email_verified=True,
        phone_verified=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_send_email():
    """
    Mock the send_email function.
    Try different paths if this doesn't work:
    - 'api.v1.services.email_service.send_email'
    - 'services.email_service.send_email'
    - 'utils.email.send_email'
    """
    print("🎯 Setting up send_email mock...")

    # Try the most common path first
    with patch("api.v1.routes.waitlist.send_email", new_callable=AsyncMock) as mock:
        # Configure the mock to return success
        mock.return_value = {"status": "success", "message": "Email sent successfully"}

        # Add debug side effect
        async def debug_send(email, subject, body):
            print(f"📧 Mock send_email called with: {email}")
            return {
                "status": "success",
                "message": f"Email sent successfully to {email}",
            }

        mock.side_effect = debug_send
        yield mock

        print(f"📞 Mock final call count: {mock.call_count}")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before all tests and cleanup after."""
    print("\n🧪 Setting up test environment...")
    yield
    print("\n🧹 Cleaning up test environment...")
    # Dispose the SQLAlchemy engine to close open connections/pools
    try:
        engine.dispose()
    except Exception:
        pass

    # Attempt to remove the SQLite file. If it's still in use, warn and skip.
    try:
        if Path("./test.db").exists():
            Path("./test.db").unlink()
    except PermissionError:
        print("⚠️  Could not delete test.db; file is still in use by another process.")
    except Exception as e:
        print(f"⚠️  Error removing test.db: {e}")


@pytest.fixture
def sample_user_data():
    """Provides sample user data for testing."""
    return {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }


def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


@pytest.fixture
def mock_google_token():
    """Sample Google ID token payload"""
    return {
        "iss": "accounts.google.com",
        "sub": "123456789",
        "email": "testuser@gmail.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
        "email_verified": True,
        "aud": "407408718192.apps.googleusercontent.com",
        "exp": 9999999999,
        "iat": 1234567890,
    }


@pytest.fixture
def sample_user(db_session):
    """Create a sample user in the database"""
    user = User(
        id=uuid.uuid4(),
        google_id="123456789",
        email="testuser@gmail.com",
        full_name="Test User",
        password_hash=None,
        is_active=True,
        email_verified=True,
        role="user",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(user)

    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        preferred_language="en",
        avatar_url="https://example.com/photo.jpg",
        timezone="Africa/Lagos",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def auth_headers(sample_user):
    """Generate valid auth headers with JWT token"""
    from api.utils.auth_utils import create_access_token

    token = create_access_token(user_id=sample_user.id, role=sample_user.role)
    return {"Authorization": f"Bearer {token}"}

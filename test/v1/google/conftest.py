# /project_root/tests/conftest.py

# This file exists to stop Pytest from automatically looking
# for fixtures in parent directories (like /project_root/conftest.py).
# google/conftest.py

import pytest
from unittest.mock import MagicMock

# IMPORTANT: Import the actual dependency function from your application
from api.db.database import get_db
from main import app  # Assuming you need the main app instance for overrides


# Create a mock database session fixture
@pytest.fixture
def mock_db_session():
    """Returns a general purpose mock DB session."""
    return MagicMock()


# This fixture automatically overrides the get_db dependency for all tests
@pytest.fixture(autouse=True)
def override_db_dependency(mock_db_session):

    # 1. Define the function that the FastAPI dependency system will call
    def override_get_db():
        # This function returns the mock session configured in the tests
        return mock_db_session

    # 2. Apply the override to the FastAPI application instance
    app.dependency_overrides[get_db] = override_get_db

    # 3. Execution yields to the test function
    yield

    # 4. Cleanup: ALWAYS clear the override after the test finishes
    app.dependency_overrides.clear()

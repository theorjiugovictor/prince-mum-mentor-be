import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from main import app
from api.v1.models.user.user import User
from api.v1.models.memories import Memory
from api.db.database import get_db
from api.utils.deps import get_current_user

client = TestClient(app)


@pytest.fixture
def mock_db_session():
    """Return a mock DB session and ensure dependency overrides are cleared."""
    session = MagicMock()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()


def _make_user():
    return User(
        id=str(uuid.uuid4()),
        email="tester@example.com",
        full_name="Tester",
        role="user",
        password_hash="hash",
        is_active=True,
    )


def _make_memory():
    return Memory(
        id=uuid.UUID(int=1),
        album_id=uuid.uuid4(),
        photo=uuid.uuid4(),
        note="A lovely memory",
        saved_on=datetime.now(timezone.utc),
    )


def test_create_memory_success(mock_db_session, monkeypatch):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    memory_obj = _make_memory()
    monkeypatch.setattr(
        "api.v1.services.memories_service.MemoriesService.create_memory",
        lambda self, payload: (memory_obj, None),
    )

    payload = {
        "album_id": str(memory_obj.album_id),
        "photo": str(memory_obj.photo),
        "note": memory_obj.note,
        "saved_on": memory_obj.saved_on.isoformat(),
    }

    response = client.post("/api/v1/memories/", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert "data" in body


@pytest.mark.parametrize(
    "error_tuple,expected_status",
    [
        ((None, (404, "Album not found")), 404),
        ((None, (404, "Photo not found")), 404),
        ((None, (409, "Memory already exists")), 409),
        ((None, (500, "Failed to create memory")), 500),
    ],
)
def test_create_memory_errors(mock_db_session, monkeypatch, error_tuple, expected_status):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    # Patch the service to return the specific error
    monkeypatch.setattr(
        "api.v1.services.memories_service.MemoriesService.create_memory",
        lambda self, payload: error_tuple,
    )

    payload = {"album_id": str(uuid.uuid4()), "photo": str(uuid.uuid4()), "note": "x"}
    response = client.post("/api/v1/memories/", json=payload)
    assert response.status_code == expected_status


def test_create_memory_invalid_payload(mock_db_session):
    # missing required fields
    # ensure auth dependency returns a user so validation runs after auth
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    response = client.post("/api/v1/memories/", json={"album_id": "not-a-uuid"})
    assert response.status_code == 422


def test_delete_memory_success(mock_db_session, monkeypatch):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    memory_id = uuid.uuid4()
    monkeypatch.setattr(
        "api.v1.services.memories_service.MemoriesService.delete_memory",
        lambda self, memory_id: (True, None),
    )

    response = client.delete(f"/api/v1/memories/{memory_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["memory_id"] == str(memory_id)


@pytest.mark.parametrize(
    "service_return,expected_status",
    [
        ((False, (404, "Memory not found")), 404),
        ((False, (500, "Failed to delete memory")), 500),
    ],
)
def test_delete_memory_errors(mock_db_session, monkeypatch, service_return, expected_status):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    memory_id = uuid.uuid4()
    monkeypatch.setattr(
        "api.v1.services.memories_service.MemoriesService.delete_memory",
        lambda self, memory_id: service_return,
    )

    response = client.delete(f"/api/v1/memories/{memory_id}")
    assert response.status_code == expected_status


def test_delete_memory_invalid_uuid(mock_db_session):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.delete("/api/v1/memories/not-a-uuid")
    assert response.status_code == 422

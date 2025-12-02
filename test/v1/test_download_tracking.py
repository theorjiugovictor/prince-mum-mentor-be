import pytest

from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from api.db.database import Base, get_db
from main import app

# Use in-memory SQLite for tests
SQLALCHEMY_TEST_URL = "sqlite+pysqlite:///:memory:"  # shared memory DB for tests
engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override dependency
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_track_download_anonymous():
    payload = {
        "download_type": "app",
        "resource_id": "android_v1",
        "file_name": "nora.apk",
        "file_url": "https://cdn.example.com/nora.apk",
        "source": "landing_page",
        "extra_metadata": {"campaign": "launch"},
    }
    resp = client.post("/api/v1/downloads/track", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["status_code"] == 201
    data = body["data"]
    assert data["download_type"] == "app"
    assert "id" in data


def test_download_stats():
    resp = client.get("/api/v1/downloads/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert isinstance(body["data"], list)

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from api.db.base_model import Base
from api.db.database import get_db

from api.v1.models.resource.resource import Resource
from api.v1.models.resource.resource_category import ResourceCategory
from api.v1.models.resource.resource_media import ResourceMedia

TEST_DATABASE_URL = "sqlite:///./test_resources_get.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def seed_data(client):
    db = TestingSessionLocal()

    cat = ResourceCategory(name="Nutrition")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    res = Resource(title="Healthy Eating", content="Eat apples.", category_id=cat.id)
    db.add(res)
    db.commit()
    db.refresh(res)

    media = ResourceMedia(
        resource_id=res.id, url="http://video.com/apples", media_type="video"
    )
    db.add(media)
    db.commit()

    db.close()
    return res


def test_get_all_resources_success(client, seed_data):
    """Test fetching resources with nested category and media"""
    response = client.get("/api/v1/resources/?page=1&limit=10")

    assert response.status_code == 200
    json_data = response.json()

    assert json_data["status"] == "success"
    assert json_data["total"] == 1

    item = json_data["data"][0]
    assert item["title"] == "Healthy Eating"

    assert item["category"]["name"] == "Nutrition"

    assert len(item["media"]) == 1
    assert item["media"][0]["url"] == "http://video.com/apples"


def test_pagination_empty(client):
    """Test fetching a page with no data"""
    response = client.get("/api/v1/resources/?page=1&limit=10")
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["data"] == []

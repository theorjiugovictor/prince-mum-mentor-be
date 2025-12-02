import pytest

from fastapi.testclient import TestClient
from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from api.db.base_model import Base
from api.db.database import get_db
from api.v1.models.user.user import User
from api.v1.models.community.posts import Post
from api.v1.models.community.post_photos import PostPhoto
from api.v1.dependencies.auth import get_current_user

TEST_DATABASE_URL = "sqlite:///./test_community_view.db"
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
    app.dependency_overrides = {}
    app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_user(client):
    db = TestingSessionLocal()
    user = User(full_name="Viewer", email="viewer@test.com", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Force Login
    app.dependency_overrides[get_current_user] = lambda: user
    return user


@pytest.fixture(scope="function")
def seed_post(client):
    db = TestingSessionLocal()
    creator = User(full_name="Poster", email="poster@test.com", is_active=True)
    db.add(creator)
    db.commit()
    db.refresh(creator)

    post = Post(user_id=creator.id, title="Secret Post", content="Shh!", views=0)
    db.add(post)
    db.commit()
    db.refresh(post)
    db.close()
    return post


def test_view_post_success(client, seed_post, test_user):
    """Test fetching a post while logged in"""
    response = client.get(f"/api/v1/community/posts/{seed_post.id}")

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Secret Post"


def test_view_post_unauthorized(client, seed_post):
    """Test fetching a post WITHOUT logging in"""

    def mock_auth_fail():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = mock_auth_fail

    response = client.get(f"/api/v1/community/posts/{seed_post.id}")
    assert response.status_code == 401


def test_view_post_increment(client, seed_post, test_user):
    """Test that viewing a post increments the view count"""
    client.get(f"/api/v1/community/posts/{seed_post.id}")
    response = client.get(f"/api/v1/community/posts/{seed_post.id}")

    assert response.status_code == 200
    assert response.json()["data"]["views"] == 2

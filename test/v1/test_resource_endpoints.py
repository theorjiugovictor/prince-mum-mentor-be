import uuid
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from api.db.database import get_db, Base
from api.utils.deps import get_current_user
from api.v1.models.user.user import User

# ==========================================
# 1. TEST DATABASE SETUP
# ==========================================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_current_user():
    return User(id=uuid.uuid4(), email="test@example.com", is_active=True)


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


# ==========================================
# 2. CATEGORY TESTS
# ==========================================


def test_create_category_success(client):
    """Test that a valid category is created successfully."""
    payload = {"name": "Artificial Intelligence"}
    response = client.post("/api/v1/resources/categories", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Category created successfully"
    assert data["data"]["name"] == "Artificial Intelligence"
    assert "id" in data["data"]


def test_create_duplicate_category_fails(client):
    """Test that creating a category with a name that already exists returns 400."""
    unique_name = f"Data Science {uuid.uuid4()}"
    payload = {"name": unique_name}

    # First creation
    client.post("/api/v1/resources/categories", json=payload)

    # Second creation (Duplicate)
    response = client.post("/api/v1/resources/categories", json=payload)

    assert response.status_code == 400
    assert "already exists" in response.json()["message"]


def test_category_lifecycle(client):
    """Tests: Get One -> Update -> Delete -> Verify Deletion"""
    # 1. Create
    create_resp = client.post(
        "/api/v1/resources/categories", json={"name": "Lifecycle Cat"}
    )
    cat_id = create_resp.json()["data"]["id"]

    # 2. Get One
    get_resp = client.get(f"/api/v1/resources/categories/{cat_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["name"] == "Lifecycle Cat"

    # 3. Update
    update_resp = client.patch(
        f"/api/v1/resources/categories/{cat_id}", json={"name": "Updated Cat"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "Updated Cat"

    # 4. Delete
    delete_resp = client.delete(f"/api/v1/resources/categories/{cat_id}")
    assert delete_resp.status_code == 200

    # 5. Verify Deletion
    check_resp = client.get(f"/api/v1/resources/categories/{cat_id}")
    assert check_resp.status_code == 404


def test_get_all_categories(client):
    """Test fetching the list of all categories."""
    client.post(
        "/api/v1/resources/categories", json={"name": f"List Cat {uuid.uuid4()}"}
    )

    response = client.get("/api/v1/resources/categories")
    assert response.status_code == 200
    assert isinstance(response.json()["data"]["categories"], list)


# ==========================================
# 3. RESOURCE CRUD TESTS
# ==========================================


def test_create_resource_success(client):
    """Test creating a resource with a valid category."""
    # Setup Category
    cat_resp = client.post(
        "/api/v1/resources/categories", json={"name": f"Cloud {uuid.uuid4()}"}
    )
    category_id = cat_resp.json()["data"]["id"]

    resource_payload = {
        "title": "Intro to Kubernetes",
        "content": "K8s content...",
        "category_id": category_id,
    }

    response = client.post("/api/v1/resources/", json=resource_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["title"] == "Intro to Kubernetes"
    assert data["data"]["category_id"] == category_id


def test_create_resource_invalid_category_fails(client):
    """Test creating a resource with a non-existent category returns 404."""
    payload = {
        "title": "Orphan Resource",
        "content": "No category",
        "category_id": str(uuid.uuid4()),  # Random UUID
    }
    response = client.post("/api/v1/resources/", json=payload)
    assert response.status_code == 404


def test_resource_update_and_delete(client):
    """Test Updating and Deleting a resource."""
    # Setup
    cat_resp = client.post(
        "/api/v1/resources/categories", json={"name": f"DevOps {uuid.uuid4()}"}
    )
    cat_id = cat_resp.json()["data"]["id"]

    # Create
    res_resp = client.post(
        "/api/v1/resources/",
        json={"title": "Old Title", "content": "x", "category_id": cat_id},
    )
    res_id = res_resp.json()["data"]["id"]

    # Update
    update_resp = client.patch(
        f"/api/v1/resources/{res_id}", json={"title": "New Title", "content": "y"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["title"] == "New Title"

    # Delete
    del_resp = client.delete(f"/api/v1/resources/{res_id}")
    assert del_resp.status_code == 200

    # Verify 404
    get_resp = client.get(f"/api/v1/resources/{res_id}")
    assert get_resp.status_code == 404


# ==========================================
# 4. UNIFIED SEARCH & FILTER TESTS
# ==========================================


def test_unified_endpoint_get_all(client):
    """Test GET /api/v1/resources/ returns list."""
    response = client.get("/api/v1/resources/")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_unified_endpoint_search(client):
    """
    Test GET /api/v1/resources/?q=...
    (Formerly /search)
    """
    # Setup Data
    cat = client.post(
        "/api/v1/resources/categories", json={"name": f"SearchCat {uuid.uuid4()}"}
    ).json()["data"]
    client.post(
        "/api/v1/resources/",
        json={"title": "Python Basics", "content": "Code", "category_id": cat["id"]},
    )
    client.post(
        "/api/v1/resources/",
        json={"title": "Cooking 101", "content": "Food", "category_id": cat["id"]},
    )

    # Search
    response = client.get("/api/v1/resources/?q=Python")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Python Basics"


def test_unified_endpoint_category_filter(client):
    """
    Test GET /api/v1/resources/?category_id=...
    (Formerly /categories/{id}/resources)
    """
    # Setup Categories
    cat_a = client.post(
        "/api/v1/resources/categories", json={"name": f"Cat A {uuid.uuid4()}"}
    ).json()["data"]
    cat_b = client.post(
        "/api/v1/resources/categories", json={"name": f"Cat B {uuid.uuid4()}"}
    ).json()["data"]

    # Setup Resources
    client.post(
        "/api/v1/resources/",
        json={"title": "Res A1", "content": "x", "category_id": cat_a["id"]},
    )
    client.post(
        "/api/v1/resources/",
        json={"title": "Res A2", "content": "x", "category_id": cat_a["id"]},
    )
    client.post(
        "/api/v1/resources/",
        json={"title": "Res B1", "content": "x", "category_id": cat_b["id"]},
    )

    # Filter by Cat A
    response = client.get(f"/api/v1/resources/?category_id={cat_a['id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    for item in data:
        assert item["category"]["id"] == cat_a["id"]


def test_unified_endpoint_search_and_filter_combined(client):
    """
    Test GET /api/v1/resources/?q=...&category_id=...
    """
    cat_tech = client.post(
        "/api/v1/resources/categories", json={"name": f"Tech {uuid.uuid4()}"}
    ).json()["data"]
    cat_news = client.post(
        "/api/v1/resources/categories", json={"name": f"News {uuid.uuid4()}"}
    ).json()["data"]

    # Both have "Daily" in title
    client.post(
        "/api/v1/resources/",
        json={"title": "Daily Tech", "content": "x", "category_id": cat_tech["id"]},
    )
    client.post(
        "/api/v1/resources/",
        json={"title": "Daily News", "content": "y", "category_id": cat_news["id"]},
    )

    # Search "Daily" AND Filter "Tech"
    response = client.get(f"/api/v1/resources/?q=Daily&category_id={cat_tech['id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Daily Tech"

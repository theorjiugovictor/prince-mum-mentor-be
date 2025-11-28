import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.v1.models.milestones import Milestone, MilestoneCategory
from api.v1.models.user.user import User
from main import app


client = TestClient(app)


@pytest.fixture
def authorized_client(client, test_user: User):
    """A client that is authorized with a test user's token."""
    from api.utils.auth_utils import create_access_token

    token = create_access_token(
        user_id=test_user.id,
        role=test_user.role if hasattr(test_user, "role") else "user",
    )

    client.headers = {"Authorization": f"Bearer {token}"}
    return client


@pytest.fixture
def test_milestone_category(db_session: Session, test_user: User):
    """Create a test milestone category."""
    category = MilestoneCategory(
        id=uuid4(),
        owner_id=test_user.id,
        owner_type="mother",
        name="Test Category",
        description="Test Description",
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def test_milestones(
    db_session: Session, test_milestone_category: MilestoneCategory, test_user: User
):
    """Create test milestones."""
    milestone1 = Milestone(
        id=uuid4(),
        owner_id=test_user.id,
        owner_type="mother",
        name="Test Milestone 1",
        description="Test Description 1",
        category_id=test_milestone_category.id,
        status="pending",
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    milestone2 = Milestone(
        id=uuid4(),
        owner_id=test_user.id,
        owner_type="mother",
        name="Test Milestone 2",
        description="Test Description 2",
        category_id=test_milestone_category.id,
        status="completed",
        created_at=datetime.utcnow() - timedelta(days=3),
        updated_at=datetime.utcnow() - timedelta(hours=12),
    )
    db_session.add_all([milestone1, milestone2])
    db_session.commit()
    return [milestone1, milestone2]


def test_get_milestones_by_category_pending(
    authorized_client, test_milestone_category, test_milestones
):
    category_id = test_milestone_category.id
    response = authorized_client.get(
        f"/api/v1/milestones/categories/{category_id}?milestone_status=pending",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["category"]["id"] == str(category_id)
    assert len(data["data"]["milestones"]) == 1
    assert data["data"]["milestones"][0]["name"] == "Test Milestone 1"
    assert data["data"]["category"]["stats"]["pending_milestones"] == 1
    assert data["data"]["category"]["stats"]["completed_milestones"] == 1


def test_get_milestones_by_category_completed(
    authorized_client, test_milestone_category, test_milestones
):
    category_id = test_milestone_category.id
    response = authorized_client.get(
        f"/api/v1/milestones/categories/{category_id}?milestone_status=completed",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["category"]["id"] == str(category_id)
    assert len(data["data"]["milestones"]) == 1
    assert data["data"]["milestones"][0]["name"] == "Test Milestone 2"
    assert data["data"]["category"]["stats"]["pending_milestones"] == 1
    assert data["data"]["category"]["stats"]["completed_milestones"] == 1


def test_get_milestones_by_category_not_found(authorized_client):
    non_existent_category_id = uuid4()
    response = authorized_client.get(
        f"/api/v1/milestones/categories/{non_existent_category_id}?milestone_status=pending",
    )
    assert response.status_code == 404


def test_get_milestones_pagination(
    authorized_client, test_milestone_category, test_milestones, db_session, test_user
):
    # Create more milestones for pagination test
    milestones = []
    for i in range(15):
        m = Milestone(
            id=uuid4(),
            owner_id=test_user.id,
            owner_type="mother",
            name=f"Test Milestone Paging {i}",
            category_id=test_milestone_category.id,
            status="pending",
        )
        milestones.append(m)
    db_session.add_all(milestones)
    db_session.commit()

    category_id = test_milestone_category.id
    # Get first page
    response = authorized_client.get(
        f"/api/v1/milestones/categories/{category_id}?milestone_status=pending&page=1&limit=10",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["milestones"]) == 10
    assert data["pagination"]["next_cursor"] == "2"
    assert data["pagination"]["prev_cursor"] is None

    # Get second page
    response = authorized_client.get(
        f"/api/v1/milestones/categories/{category_id}?milestone_status=pending&page=2&limit=10",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    # 1 from test_milestones + 15 from this test = 16. So 6 on the second page.
    assert len(data["milestones"]) == 6
    assert data["pagination"]["next_cursor"] is None
    assert data["pagination"]["prev_cursor"] == "1"


def test_get_milestone_summary(authorized_client, test_milestones):
    response = authorized_client.get("/api/v1/milestones/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["created_milestones"] == 2
    assert data["data"]["completed_milestones"] == 1


def test_get_milestone_summary_with_duration(authorized_client, test_milestones):
    response = authorized_client.get("/api/v1/milestones/summary?duration=day")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["created_milestones"] == 0
    assert data["data"]["completed_milestones"] == 1 

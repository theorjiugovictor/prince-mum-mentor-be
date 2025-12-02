import pytest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routes.faq import router as faq_router
from api.v1.services.faq import FAQService


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(faq_router)
    return TestClient(app)


def test_get_faqs_success(client):
    mock_data = (
        (
            [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "category": "general",
                    "question": "Mock question?",
                    "answer": "Mock answer.",
                    "keywords": {},
                    "view_count": 0,
                    "helpful_count": 0,
                    "order_index": 0,
                    "created_at": "2025-01-01T00:00:00",
                }
            ],
            1,
        ),
        None,
    )

    with patch.object(FAQService, "fetch_faqs", Mock(return_value=mock_data)):
        response = client.get("/faqs")

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "success"
    assert body["data"]["data"][0]["question"] == "Mock question?"


def test_get_faqs_incorrect_input(client):
    response = client.get("/faqs?limit=-5")
    print("@@", response.status_code)

    assert response.status_code == 422
    assert "greater than" in response.json()["detail"][0]["msg"].lower()


def test_get_faqs_expected_error(client):
    # Make the service return an error (not raise)
    mock_data = ((None, None), "Boom")

    with patch.object(FAQService, "fetch_faqs", Mock(return_value=mock_data)):
        response = client.get("/faqs")

    assert response.status_code == 500
    assert response.json()["message"] == "Boom"

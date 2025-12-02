from unittest.mock import patch, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient


def test_delete_task_success(client: TestClient, auth_headers):
    task_id = uuid4()

    with patch("api.v1.routes.delete_task.TaskService") as mock_service:
        mock_service.get_task_by_id.return_value = MagicMock()
        mock_service.delete_task.return_value = True

        response = client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)

        assert response.status_code == 204


def test_delete_task_not_found(client: TestClient, auth_headers):
    task_id = uuid4()

    with patch("api.v1.routes.delete_task.TaskService") as mock_service:
        mock_service.get_task_by_id.return_value = None

        response = client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)

        assert response.status_code == 404
        assert response.json()["message"] == "Task not found"

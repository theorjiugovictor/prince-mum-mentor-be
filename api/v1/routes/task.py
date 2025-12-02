"""
This module contains the API endpoints for managing tasks.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.utils.responses import fail_response, success_response
from api.v1.models.user.user import User
from api.v1.schemas.task import (
    CreateTaskRequest,
    EditTaskRequest,
    ListTasksQuery,
    TaskResponse,
    TaskStatusUpdate,
)
from api.v1.services.task_service import TaskService, create_task

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_task_endpoint(
    request: CreateTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new task.
    """
    logger.info("Entered create_task endpoint")
    task = create_task(request, db, current_user)

    return success_response(
        status_code=201, message="Task created successfully", data=task
    )


@router.delete("/{task_id}")
def delete_task_endpoint(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a task"""
    try:
        task_service = TaskService(db)
        task = task_service.get_task_by_id(task_id, current_user.id)

        if not task:
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND, message="Task not found"
            )

        success = TaskService.delete_task(db, task)

        if not success:
            return fail_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to delete task",
            )
        return success_response(
            status_code=status.HTTP_200_OK, message="Task deleted successfully"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Error deleting task: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the task",
        ) from e


@router.patch("/{task_id}")
def edit_task(
    task_id: UUID,
    request_data: EditTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Edit an existing task.
    """
    try:

        task_service = TaskService(db)
        task = task_service.get_task_by_id(task_id, current_user.id)

        if not task:
            logger.warning("Task %s not found for user %s", task_id, current_user.id)
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND, message="Task not found"
            )

        updated_task, error = task_service.update_task(task, request_data)

        if error:
            logger.error("Error updating task %s: %s", task_id, error)
            return fail_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Failed to update task",
            )

        response_data = {
            "id": str(updated_task.id),
            "name": updated_task.name,
            "description": updated_task.description,
            "due_date": (
                updated_task.due_date.isoformat() if updated_task.due_date else None
            ),
            "status": updated_task.status,
            "completed_at": (
                updated_task.completed_at.isoformat()
                if updated_task.completed_at
                else None
            ),
            "created_at": updated_task.created_at.isoformat(),
            "updated_at": updated_task.updated_at.isoformat(),
        }

        logger.info("Task %s updated successfully by user %s", task_id, current_user.id)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Task updated successfully",
            data=response_data,
        )

    except ValueError as ve:
        logger.error("Validation error: %s", str(ve))
        return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=str(ve))
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error editing task: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get("/")
def list_tasks(
    query: ListTasksQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get paginated list of tasks for the current user with optional status filter and ordering.
    """
    logger.info(
        "Fetching tasks for user_id=%s | page=%s | per_page=%s | status=%s",
        current_user.id,
        query.page,
        query.per_page,
        query.task_status,
    )

    try:
        # Validate status filter
        if query.task_status and query.task_status not in ["pending", "completed"]:
            return fail_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid status filter",
                context={"allowed": ["pending", "completed"]},
            )

        # Validate order_by field
        allowed_order_fields = [
            "due_date",
            "created_at",
            "updated_at",
            "name",
            "status",
        ]
        if query.order_by not in allowed_order_fields:
            return fail_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid order_by field",
                context={"allowed": allowed_order_fields},
            )

        # Validate order_direction
        if query.order_direction not in ["asc", "desc"]:
            return fail_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid order_direction",
                context={"allowed": ["asc", "desc"]},
            )

        task_service = TaskService(db)

        tasks, total_count = task_service.get_user_tasks(
            user_id=current_user.id,
            page=query.page,
            per_page=query.per_page,
            status=query.task_status,
            order_by=query.order_by,
            order_direction=query.order_direction,
        )

        # Prepare task response list
        tasks_data = [
            {
                "id": str(task.id),
                "name": task.name,
                "description": task.description,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "status": task.status,
                "completed_at": (
                    task.completed_at.isoformat() if task.completed_at else None
                ),
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
            for task in tasks
        ]

        # Pagination calculations
        total_pages = (
            (total_count + query.per_page - 1) // query.per_page
            if total_count > 0
            else 1
        )

        response_data = {
            "details": tasks_data,
            "pagination": {
                "page": query.page,
                "per_page": query.per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "next": query.page + 1 if query.page < total_pages else None,
                "prev": query.page - 1 if query.page > 1 else None,
            },
        }

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Tasks retrieved successfully",
            data=response_data,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Error listing tasks: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving tasks",
        ) from e


@router.patch("/{task_id}/status", response_model=TaskResponse)
def toggle_task_completion(
    task_id: str,
    status_update: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Toggles the completion status of a task.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        task_uuid = UUID(task_id)
        user_uuid = UUID(str(current_user.id))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid UUID format",
        ) from exc

    task_service = TaskService(db)
    task = task_service.toggle_completion(
        task_id=task_uuid, completed=status_update.completed, user_id=user_uuid
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task

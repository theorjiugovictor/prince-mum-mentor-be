from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.services.task_service import TaskService
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("/")
def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    task_status: Optional[str] = Query(  # CHANGED: status -> task_status
        None , description="Filter by status"
    ),
    order_by: Optional[str] = Query(
        "due_date", description="Field to order by: due_date, created_at, updated_at, name, status"
    ),
    order_direction: Optional[str] = Query(
        "asc", description="Order direction: asc or desc"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get paginated list of tasks for the current user with optional status filter and ordering.
    """
    logger.info(
        f"Fetching tasks | user_id={current_user.id} | page={page} | per_page={per_page} | status={task_status} | order_by={order_by} | order_direction={order_direction}"
    )

    try:
        # Validate status filter
        if task_status and task_status not in ["pending", "completed"]:  # CHANGED
            return fail_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid status filter",
                context={"allowed": ["pending", "completed"]},
            )
            
        # Validate order_by field
        allowed_order_fields = ["due_date", "created_at", "updated_at", "name", "status"]
        if order_by not in allowed_order_fields:
            return fail_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid order_by field",
                context={"allowed": allowed_order_fields},
            )

        # Validate order_direction
        if order_direction not in ["asc", "desc"]:
            return fail_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid order_direction",
                context={"allowed": ["asc", "desc"]},
            )

        task_service = TaskService(db)

        tasks, total_count = task_service.get_user_tasks(
            user_id=current_user.id,
            page=page,
            per_page=per_page,
            status=task_status,  # CHANGED
            order_by=order_by,
            order_direction=order_direction,
        )

        # Prepare task response list
        tasks_data = [
            {
                "id": str(task.id),
                "name": task.name,
                "description": task.description,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "status": task.status,
                "completed_at": task.completed_at.isoformat()
                if task.completed_at
                else None,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
            for task in tasks
        ]

        # Pagination calculations
        total_pages = (
            (total_count + per_page - 1) // per_page if total_count > 0 else 1
        )

        response_data = {
            "details": tasks_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "next": page + 1 if page < total_pages else None,
                "prev": page - 1 if page > 1 else None,
            },
        }

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Tasks retrieved successfully",
            data=response_data,
        )

    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")

        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while retrieving tasks",
            context={"error": str(e)},
        )

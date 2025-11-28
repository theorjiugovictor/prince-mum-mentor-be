from uuid import UUID
from typing import Optional, Tuple, List
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import nulls_last, asc, desc

from api.v1.models.task import Task
from api.v1.models.user.user import User
from api.v1.schemas.task import CreateTaskRequest, EditTaskRequest
from api.utils.logger import logger
from fastapi import HTTPException, status
from sqlalchemy import func

def create_task(request: CreateTaskRequest, db: Session, current_user: User) -> Task:
    """Create a new task for the current user"""

    try:
        logger.info(f"Creating task for user {current_user.id}")

        # Create task
        task = Task(
            user_id=current_user.id,
            name=request.name.strip(),
            description=request.description,
            due_date=request.due_date,
            status="pending",
            completed_at=None
        )

        task.insert(db)

        logger.info(f"Task created successfully for user {current_user.id}")
        return task

    except Exception as e:
        logger.error(f"Error creating task for user {current_user.id}: {e}")
        raise


class TaskService:
    """Service for task operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_task_by_id(self, task_id: UUID, user_id: UUID) -> Optional[Task]:
        """
        Retrieve a task by ID for a specific user.

        Args:
            task_id: UUID of the task
            user_id: UUID of the user who owns the task

        Returns:
            Task object if found, None otherwise
        """
        try:
            task = (
                self.db.query(Task)
                .filter(Task.id == task_id, Task.user_id == user_id)
                .first()
            )
            return task
        except Exception as e:
            logger.error(f"Error retrieving task: {str(e)}")
            return None

    def get_user_tasks(
            self,
            user_id: UUID,
            page: int = 1,
            per_page: int = 10,
            status: Optional[str] = None,
            order_by: Optional[str] = "due_date",
            order_direction: Optional[str] = "asc"
    ):

        try:
            query = self.db.query(Task).filter(Task.user_id == user_id)

            if status:
                query = query.filter(Task.status == status)

            # Apply ordering
            order_field = getattr(Task, order_by, Task.due_date)
            order_func = asc if order_direction == "asc" else desc

            # Use nulls_last for fields that can be null
            if order_by in ["due_date", "completed_at"]:
                query = query.order_by(nulls_last(order_func(order_field)))
            else:
                query = query.order_by(order_func(order_field))

            total_count = query.count()

            offset = (page - 1) * per_page
            tasks = query.offset(offset).limit(per_page).all()

            return tasks, total_count

        except SQLAlchemyError as db_err:
            logger.error(f"[DB ERROR] retrieving tasks for user {user_id}: {db_err}")
            raise

        except Exception as e:
            logger.error(f"[UNEXPECTED ERROR] retrieving tasks for user {user_id}: {e}")
            raise


    def toggle_completion(
        self, task_id: UUID, completed: bool, user_id: UUID
    ) -> Optional[Task]:
        """
        Toggles the completion status of a task.

        Args:
            task_id: UUID of the task
            completed: Boolean indicating the completion status
            user_id: UUID of the user who owns the task

        Returns:
            Updated task object if found, None otherwise
        """
        task = self.get_task_by_id(task_id, user_id)
        if not task:
            return None

        if completed:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
        else:
            task.status = "pending"
            task.completed_at = None

        try:
            self.db.commit()
            self.db.refresh(task)
            return task
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error toggling task completion: {str(e)}")
            return None

    def update_task(
        self, task: Task, update_data: EditTaskRequest
    ) -> Tuple[Optional[Task], Optional[str]]:
        """
        Update a task with the provided data.

        Args:
            task: Task object to update
            update_data: EditTaskRequest with fields to update

        Returns:
            Tuple of (updated_task, error_message)
        """
        try:
            update_dict = update_data.model_dump(exclude_unset=True)

            if "status" in update_dict:
                task.status = update_dict["status"]
                if task.status == "completed":
                    task.completed_at = datetime.now(timezone.utc)
                else:
                    task.completed_at = None
                del update_dict["status"]

            if "due_date" in update_dict and update_dict["due_date"] is not None:
                task.due_date = datetime.fromisoformat(update_dict["due_date"].replace('Z', '+00:00'))
                del update_dict["due_date"]

            for field, value in update_dict.items():
                setattr(task, field, value)

            self.db.commit()
            self.db.refresh(task)

            logger.info(f"Task {task.id} updated successfully")
            return task, None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating task: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_task(db: Session, task: Task) -> bool:
        """
        Hard delete a task from the database.
        
        Args:
            db: Database session
            task: Task object to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            db.delete(task)
            db.commit()
            logger.info(f"Task {task.id} deleted successfully")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting task {task.id}: {str(e)}")
            return False
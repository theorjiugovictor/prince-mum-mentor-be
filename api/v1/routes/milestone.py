from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.responses import success_response
from api.v1.schemas.milestone import MilestoneCreate, MilestoneResponse, MilestoneToggle, MilestoneUpdate
from api.v1.services.milestone import MilestoneService

router = APIRouter(prefix="/milestones", tags=["Milestones"])

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_milestone(
    payload: MilestoneCreate,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new milestone for Mother or Child.
    
    This endpoint allows authenticated mothers to create milestones for themselves or their children.
    
    **Behavior:**
    - If `child_id` is provided: Creates a milestone for the specified child (validates child belongs to mother)
    - If `child_id` is omitted: Creates a milestone for the mother herself
    
    **Categories by Owner Type:**
    - Mother: "Body Recovery", "Mental Wellness", "Routine Builder", "Self Care"
    - Child: "Development", "Health and Nutrition", "Activities and Play", "Growth Check"
    
    **Request Body:**
    - name (required): Milestone title
    - description (optional): Detailed description
    - category (required): Must match the owner type (mother/child)
    - child_id (optional): UUID of the child if creating for child
    
    **Returns:** Created milestone with status "pending"
    """
    milestone = MilestoneService.create(session, current_user.id, payload)
    
    response_data = MilestoneResponse.model_validate(milestone).model_dump()

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Milestone created successfully",
        data=response_data
    )

@router.patch("/{milestone_id}/status", status_code=status.HTTP_201_CREATED)
def toggle_milestone_status(
    milestone_id: uuid.UUID,
    payload: MilestoneToggle,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Toggle milestone status between 'pending' and 'completed'.
    
    This endpoint allows mothers to mark milestones as completed or revert them to pending.
    
    **Security:**
    - Only the milestone owner can toggle its status
    - For child milestones, validates that the child belongs to the requesting mother
    
    **Request Body:**
    - completed (required): true to mark as completed, false to mark as pending
    - child_id (optional): Not currently used but kept for backward compatibility
    
    **Returns:** Updated milestone with new status
    """
    milestone = MilestoneService.toggle_status(session, current_user.id, milestone_id, payload)

    response_data = MilestoneResponse.model_validate(milestone).model_dump()

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Milestone status updated successfully",
        data=response_data
    )

@router.put("/{milestone_id}", status_code=status.HTTP_200_OK)
def update_milestone(
    milestone_id: uuid.UUID,
    payload: MilestoneUpdate,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update milestone details (name, description, category).
    
    This endpoint allows partial updates to milestone information.
    
    **Security:**
    - Only the milestone owner can update it
    - For child milestones, validates that the child belongs to the requesting mother
    
    **Request Body (all fields optional):**
    - name: New milestone title
    - description: New description
    - category: New category (must still match owner type)
    
    **Returns:** Updated milestone with all current data
    """
    milestone = MilestoneService.update(session, current_user.id, milestone_id, payload)
    
    response_data = MilestoneResponse.model_validate(milestone).model_dump()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Milestone updated successfully",
        data=response_data
    )

@router.delete("/{milestone_id}", status_code=status.HTTP_200_OK)
def delete_milestone(
    milestone_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Permanently delete a milestone.
    
    This endpoint removes a milestone from the database.
    
    **Security:**
    - Only the milestone owner can delete it
    - For child milestones, validates that the child belongs to the requesting mother
    
    **Warning:** This action cannot be undone
    
    **Returns:** Success message confirming deletion
    """
    MilestoneService.delete(session, current_user.id, milestone_id)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Milestone deleted successfully",
        data={}
    )

@router.get("/pending", status_code=status.HTTP_200_OK)
def get_pending_milestones(
    child_id: Optional[uuid.UUID] = Query(None),
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all pending milestones for Mother or Child.
    
    Retrieves only milestones with status "pending" (not yet completed).
    
    **Query Parameters:**
    - child_id (optional): If provided, returns pending milestones for that child.
                          If omitted, returns mother's pending milestones.
    
    **Security:**
    - For child milestones, validates that the child belongs to the requesting mother
    
    **Returns:** List of pending milestones ordered by creation date (oldest first)
    """
    milestones = MilestoneService.get_pending(session, current_user.id, child_id)
    
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Pending milestones retrieved successfully",
        data={
            "details": [
                MilestoneResponse.model_validate(m).model_dump() 
                for m in milestones
            ]
        }
    )

@router.get("/", status_code=status.HTTP_200_OK)
def get_all_milestones(
    child_id: Optional[uuid.UUID] = Query(None, description="Filter by child ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all milestones with optional filters.
    
    Retrieves all milestones (both pending and completed) with optional filtering.
    
    **Query Parameters:**
    - child_id (optional): If provided, returns milestones for that child.
                          If omitted, returns mother's milestones.
    - category (optional): Filter by specific category (must match owner type)
    
    **Security:**
    - For child milestones, validates that the child belongs to the requesting mother
    
    **Returns:** List of milestones ordered by creation date (newest first)
    """
    milestones = MilestoneService.get_all(session, current_user.id, child_id, category)
    
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Milestones retrieved successfully",
        data={
            "details": [
                MilestoneResponse.model_validate(m).model_dump() 
                for m in milestones
            ]
        }
    )

@router.get("/progress", status_code=status.HTTP_200_OK)
def get_milestone_progress(
    child_id: Optional[uuid.UUID] = Query(None, description="Filter by child ID"),
    session: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get overall milestone progress statistics.
    
    Returns counts of pending and completed milestones for tracking progress.
    
    **Query Parameters:**
    - child_id (optional): If provided, returns progress for that child.
                          If omitted, returns mother's progress.
    
    **Security:**
    - For child milestones, validates that the child belongs to the requesting mother
    
    **Returns:** 
    - pending_milestones: Number of incomplete milestones
    - completed_milestones: Number of completed milestones
    """
    progress_data = MilestoneService.get_progress(session, current_user.id, child_id)
    
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Milestone progress retrieved successfully",
        data=progress_data
    )

@router.get("/categories", status_code=status.HTTP_200_OK)
def get_available_categories(
    child_id: Optional[uuid.UUID] = Query(None, description="If provided, returns child categories; otherwise returns mother categories")
):
    """
    Get available milestone categories based on owner type.
    
    Returns the appropriate set of categories depending on whether the milestone
    is for a mother or child.
    
    **Query Parameters:**
    - child_id (optional): If provided, returns child categories.
                          If omitted, returns mother categories.
    
    **Mother Categories:**
    - Body Recovery
    - Mental Wellness
    - Routine Builder
    - Self Care
    
    **Child Categories:**
    - Development
    - Health and Nutrition
    - Activities and Play
    - Growth Check
    
    **Returns:** List of available categories with value and label
    """
    from api.v1.models.milestones import MotherCategory, ChildCategory
    
    if child_id:
        # Return child categories
        categories = [
            {"value": cat.value, "label": cat.value}
            for cat in ChildCategory
        ]
    else:
        # Return mother categories
        categories = [
            {"value": cat.value, "label": cat.value}
            for cat in MotherCategory
        ]
    
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Categories retrieved successfully",
        data={"categories": categories}
    )
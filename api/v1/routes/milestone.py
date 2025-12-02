"""
This module contains the API endpoints for managing milestones.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.responses import success_response
from api.v1.models.milestones import MotherCategory, ChildCategory
from api.v1.schemas.milestone import (
    MilestoneCreate,
    MilestoneResponse,
    MilestoneToggle,
    MilestoneUpdate,
)
from api.v1.services.milestone import MilestoneService

router = APIRouter(prefix="/milestones", tags=["Milestones"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_milestone(
    payload: MilestoneCreate,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new milestone for Mother or Child.
    """
    milestone = MilestoneService.create(session, current_user.id, payload)

    response_data = MilestoneResponse.model_validate(milestone).model_dump()

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Milestone created successfully",
        data=response_data,
    )


@router.patch("/{milestone_id}/status", status_code=status.HTTP_201_CREATED)
def toggle_milestone_status(
    milestone_id: uuid.UUID,
    payload: MilestoneToggle,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Toggle milestone status between 'pending' and 'completed'.
    """
    milestone = MilestoneService.toggle_status(
        session, current_user.id, milestone_id, payload
    )

    response_data = MilestoneResponse.model_validate(milestone).model_dump()

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Milestone status updated successfully",
        data=response_data,
    )


@router.put("/{milestone_id}", status_code=status.HTTP_200_OK)
def update_milestone(
    milestone_id: uuid.UUID,
    payload: MilestoneUpdate,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update milestone details (name, description, category).
    """
    milestone = MilestoneService.update(
        session, current_user.id, milestone_id, payload
    )

    response_data = MilestoneResponse.model_validate(milestone).model_dump()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Milestone updated successfully",
        data=response_data,
    )


@router.delete("/{milestone_id}", status_code=status.HTTP_200_OK)
def delete_milestone(
    milestone_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Permanently delete a milestone.
    """
    MilestoneService.delete(session, current_user.id, milestone_id)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Milestone deleted successfully",
        data={},
    )


@router.get("/pending", status_code=status.HTTP_200_OK)
def get_pending_milestones(
    child_id: Optional[uuid.UUID] = Query(None),
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get all pending milestones for Mother or Child.
    """
    milestones = MilestoneService.get_pending(session, current_user.id, child_id)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Pending milestones retrieved successfully",
        data={
            "details": [
                MilestoneResponse.model_validate(m).model_dump() for m in milestones
            ]
        },
    )


@router.get("/", status_code=status.HTTP_200_OK)
def get_all_milestones(
    child_id: Optional[uuid.UUID] = Query(None, description="Filter by child ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get all milestones with optional filters.
    """
    milestones = MilestoneService.get_all(
        session, current_user.id, child_id, category
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Milestones retrieved successfully",
        data={
            "details": [
                MilestoneResponse.model_validate(m).model_dump() for m in milestones
            ]
        },
    )


@router.get("/progress", status_code=status.HTTP_200_OK)
def get_milestone_progress(
    child_id: Optional[uuid.UUID] = Query(None, description="Filter by child ID"),
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get overall milestone progress statistics.
    """
    progress_data = MilestoneService.get_progress(session, current_user.id, child_id)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Milestone progress retrieved successfully",
        data=progress_data,
    )


@router.get("/categories", status_code=status.HTTP_200_OK)
def get_available_categories(
    child_id: Optional[uuid.UUID] = Query(
        None,
        description="If provided, returns child categories; otherwise returns mother categories",
    )
):
    """
    Get available milestone categories based on owner type.
    """
    if child_id:
        # Return child categories
        categories = [{"value": cat.value, "label": cat.value} for cat in ChildCategory]
    else:
        # Return mother categories
        categories = [
            {"value": cat.value, "label": cat.value} for cat in MotherCategory
        ]

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Categories retrieved successfully",
        data={"categories": categories},
    )

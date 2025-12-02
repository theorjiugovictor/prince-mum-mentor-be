"""
This module contains the API endpoints for managing journal entries.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.logger import logger
from api.utils.responses import success_response
from api.v1.models.user.user import User
from api.v1.schemas.journal import (
    JournalCreateRequest,
    JournalCreateResponse,
    JournalEdit,
    JournalResponse,
    JournalData,
    GetAllJournalsQuery,
)
from api.v1.services.journal_service import JournalService
from api.v1.services.get_entry_by_category import get_entries_by_category


router = APIRouter(prefix="/journal", tags=["Journal"])


@router.post("/entry/", response_model=None)
def create_journal(
    journal_data: JournalCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new journal entry.

    This endpoint allows an authenticated user to create a new journal entry.
    """
    logger.info("Creating journal for user_id=%s", current_user.id)

    journal = JournalService.create_journal(db, journal_data, str(current_user.id))

    if not journal:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create journal entry",
        )

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Journal created successfully",
        data=JournalCreateResponse(
            journal_entry_id=journal.id, title=journal.title
        ).model_dump(),
    )


@router.delete("/{entry_id}", status_code=status.HTTP_200_OK)
def delete_journal_entry(
    entry_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a specific journal entry.
    """
    JournalService.delete_journal(session, entry_id, current_user.id)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Journal entry deleted successfully",
        data=None,
    )


@router.patch(
    "/{entry_id}", status_code=status.HTTP_200_OK, response_model=JournalResponse
)
def edit_journal_entry(
    entry_id: uuid.UUID,
    payload: JournalEdit,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Edit a specific journal entry.
    """
    updated_journal = JournalService.update_journal(
        session, entry_id, current_user.id, payload
    )

    response_data = JournalData.model_validate(updated_journal).model_dump()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Successfully edited entry",
        data=response_data,
    )


@router.get("/by-category")
async def get_journal_entry_by_category(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: str = Query(..., description="Category name to search for"),
    limit: int = Query(10, description="Number of entries to return", ge=1, le=100),
    offset: int = Query(0, description="Number of entries to skip", ge=0),
):
    """
    Retrieves journal entries by category with pagination.
    """
    try:
        filtered_journal_entries = get_entries_by_category(
            db=db,
            category_title=category,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )

        return success_response(
            status_code=200,
            message=f"Journal entries for category '{category}'",
            data=filtered_journal_entries,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving journal entries",
        ) from e


@router.get("/entries")
async def get_all_journal_entries(
    query_params: GetAllJournalsQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all journal entries for the authenticated user.

    Returns paginated journal entries with optional sorting.
    """
    try:
        result = JournalService.get_all_journals(
            db=db,
            user_id=str(current_user.id),
            limit=query_params.limit,
            offset=query_params.offset,
            sort_by=query_params.sort_by,
            order=query_params.order,
        )

        return success_response(
            status_code=200,
            message="Journal entries retrieved successfully",
            data={
                "entries": result["entries"],
                "total": result["total"],
                "limit": query_params.limit,
                "offset": query_params.offset,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving journal entries",
        ) from e

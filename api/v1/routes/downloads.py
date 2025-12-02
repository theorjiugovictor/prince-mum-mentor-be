
"""
This module contains the API endpoints for tracking downloads.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Request, Query, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.v1.schemas.downloads import DownloadTrackRequest
from api.v1.services.download_tracking import log_download_event, get_download_stats
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger

router = APIRouter(prefix="/downloads", tags=["Downloads"])


@router.post("/track", status_code=status.HTTP_201_CREATED)
async def track_download(
    payload: DownloadTrackRequest, request: Request, db: Session = Depends(get_db)
):
    """
    Track a download event.
    """
    event, error = log_download_event(
        db, request, payload, user_id=None, session_id=None
    )
    if error:
        logger.error("track_download_error: %s", error)
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=error
        )
    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Download tracked",
        data={
            "id": str(event.id),
            "download_type": event.download_type,
            "occurred_at": event.occurred_at.isoformat(),
        },
    )


@router.get("/stats")
async def download_stats(
    db: Session = Depends(get_db),
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    group_by: str = Query("download_type"),
):
    """
    Get download statistics.
    """
    data, error = get_download_stats(
        db, from_dt=from_dt, to_dt=to_dt, group_by=group_by
    )
    if error:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if "group_by" in error.lower()
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        return fail_response(status_code=status_code, message=error)
    return success_response(status_code=200, message="Download stats", data=data)


"""
This module contains the API endpoints for fetching FAQs.
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.responses import fail_response, success_response
from api.v1.services.faq import FAQService
from api.v1.schemas.faq import FAQListResponse, FAQResponse
from api.utils.logger import logger

router = APIRouter(prefix="/faqs", tags=["FAQ"])


@router.get("/", response_model=FAQListResponse)
def get_faqs(
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db),
):
    """
    Get a list of FAQs with optional filtering and pagination.
    """
    (faqs, total), error = FAQService.fetch_faqs(
        session=session,
        category=category,
        search=search,
        limit=limit,
        offset=offset,
    )

    if error:
        logger.error("FAQ fetch failed: %s", error)
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error,
        )

    if faqs is None:
        logger.error("FAQ fetch returned None without error")
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unable to retrieve FAQs",
        )

    logger.info("FAQs retrieved successfully (%s items)", len(faqs))

    response_data = FAQListResponse(
        data=[FAQResponse.model_validate(f) for f in faqs],
        meta={
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="FAQs retrieved successfully",
        data=response_data.model_dump(),
    )


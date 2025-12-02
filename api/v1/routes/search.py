"""
This module contains the API endpoints for searching.
"""
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from api.utils.deps import get_current_user
from api.db.database import get_db
from api.utils.responses import success_response, fail_response
from api.v1.services.gallery_search_service import search_gallery
from api.v1.schemas.gallery_search import SearchResultItem

router = APIRouter(tags=["Home"])


@router.get("/search")
def search(
    q: str | None = Query(None, min_length=1),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Search albums and memory notes for the authenticated user."""
    try:
        if not q or not q.strip():
            return success_response(200, "No query provided", {"results": []})

        raw = search_gallery(db, current_user.id, q, limit=limit, offset=offset)

        # Validate/serialize via pydantic
        items: List[SearchResultItem] = [
            SearchResultItem.model_validate(r) for r in raw
        ]

        return success_response(
            200, "Search results", {"results": [i.model_dump() for i in items]}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return fail_response(500, "Search failed", {"error": str(e)})

"""
This module contains the API endpoints for managing resources.
"""

import math
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.utils.responses import fail_response, success_response
from api.v1.models.user.user import User
from api.v1.schemas.resource import (
    CreateResourceBookmark,
    PaginatedResourceResponse,
    ResourceResponse,
    ResourceCreate,
    CategoryCreate,
    ResourceUpdate,
)
from api.v1.services.resource import ResourceService
from api.v1.services.resource_media import ResourceMediaService
from api.v1.services.create_resource_bookmark import create_resource_bookmark
from api.utils.logger import logger

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("/media/{media_id}", status_code=status.HTTP_200_OK)
def view_resource_media(
    media_id: UUID,
    session: Session = Depends(get_db),
):
    """
    View a single media file (photo or video) from a community post.

    This endpoint retrieves details of a specific media file associated with
    a community resource post.

    **Path Parameters:**
    - media_id (required): UUID of the media file to view

    **Authentication:**
    - Requires valid access token

    **Returns:**
    - Media details including:
      - id: Media UUID
      - resource_id: UUID of the post this media belongs to
      - url: Direct URL to the media file
      - media_type: Either "photo" or "video"

    **Example Response:**
    ```json
    {
      "status": "success",
      "status_code": 200,
      "message": "Media retrieved successfully",
      "data": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "resource_id": "987fcdeb-51a2-43f7-b123-456789abcdef",
        "url": "https://example.com/media/video.mp4",
        "media_type": "video"
      }
    }
    ```

    **Error Responses:**
    - 404: Media not found
    - 401: Unauthorized (invalid or missing token)
    """
    media_data = ResourceMediaService.get_media_by_id(session, media_id)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Media retrieved successfully",
        data=media_data,
    )





@router.get("/search", status_code=status.HTTP_200_OK)
def search_resources(
    title: str = Query(..., min_length=1, description="Search title"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_db),
):
    """
    Search resources by title substring (case-insensitive).
    """

    try:
        resources, total = ResourceService.search_by_title(
            session=session, title=title, page=page, limit=limit
        )

        if not resources:
            return fail_response(
                status_code=404, message="No resources found", context={"title": title}
            )

        data = [ResourceResponse.model_validate(r) for r in resources]
        total_pages = (total + limit - 1) // limit

        payload = {
            "status": "success",
            "message": "Resources retrieved successfully",
            "data": data,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

        return success_response(
            status_code=200, message="Resources retrieved successfully", data=payload
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search resources",
        ) from e


@router.post("/bookmarks/")
async def save_resource_for_later(
    payload: CreateResourceBookmark,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a bookmark for a resource for the current user.

    This endpoint allows an authenticated user to save a resource for later access (bookmark).
    It expects a payload with the resource ID, and will associate the resource with the user.
    Returns a success response with the bookmark details, or an error if the operation fails.
    """
    try:
        new_bookmark = create_resource_bookmark(
            db, current_user.id, payload.resource_id
        )
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Successfully created resource for later",
            data=new_bookmark,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong while trying to save your resource bookmark",
        ) from e





# ==========================
# CATEGORY ROUTES
# (Must come before /{resource_id} routes to avoid path conflicts)
# ==========================


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    schema: CategoryCreate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new category for resources."""
    try:
        category = ResourceService.create_category(session, schema)
        return success_response(
            message="Category created successfully",
            status_code=201,
            data={"id": category.id, "name": category.name},
        )
    except HTTPException as e:
        logger.error(
            f"HTTP error creating category {e.status_code}: {str(e)}", exc_info=True
        )
        return fail_response(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}", exc_info=True)
        return fail_response(message="Failed to create category", status_code=500)


@router.get("/categories", status_code=status.HTTP_200_OK)
async def get_all_categories(session: Session = Depends(get_db)):
    """Get all resource categories."""
    try:
        categories = ResourceService.get_all_categories(session)
        data = [{"id": cat.id, "name": cat.name} for cat in categories]

        return success_response(
            message="Categories retrieved successfully",
            status_code=200,
            data={"categories": data},
        )
    except Exception as e:
        logger.error(f"Error retrieving categories: {str(e)}", exc_info=True)
        return fail_response(message="Failed to retrieve categories", status_code=500)


@router.get("/categories/{category_id}", status_code=status.HTTP_200_OK)
async def get_category_by_id(category_id: UUID, session: Session = Depends(get_db)):
    """Get a single resource category by ID."""
    try:
        category = ResourceService.get_category_by_id(session, category_id)
        return success_response(
            message="Category retrieved successfully",
            status_code=200,
            data={"id": category.id, "name": category.name},
        )
    except HTTPException as e:
        logger.error(
            f"HTTP error retrieving category {e.status_code}: {str(e)}", exc_info=True
        )
        return fail_response(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error retrieving category: {str(e)}", exc_info=True)
        return fail_response(message="Failed to retrieve category", status_code=500)


@router.patch("/categories/{category_id}", status_code=status.HTTP_200_OK)
async def update_category(
    category_id: UUID,
    schema: CategoryCreate,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update a resource category by ID."""
    try:
        category = ResourceService.update_category(session, category_id, schema)
        return success_response(
            message="Category updated successfully",
            status_code=200,
            data={"id": category.id, "name": category.name},
        )
    except HTTPException as e:
        logger.error(
            f"HTTP error updating category {e.status_code}: {str(e)}", exc_info=True
        )
        return fail_response(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error updating category: {str(e)}", exc_info=True)
        return fail_response(message="Failed to update category", status_code=500)


@router.delete("/categories/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(
    category_id: UUID,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a resource category by ID."""
    try:
        ResourceService.delete_category(session, category_id)
        return success_response(
            message="Category deleted successfully", status_code=200, data=None
        )
    except HTTPException as e:
        logger.error(
            f"HTTP error deleting category {e.status_code}: {str(e)}", exc_info=True
        )
        return fail_response(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}", exc_info=True)
        return fail_response(message="Failed to delete category", status_code=500)


# ==========================
# RESOURCE ROUTES
# ==========================


@router.get(
    "/", status_code=status.HTTP_200_OK, response_model=PaginatedResourceResponse
)
async def get_resources(
    q: Optional[str] = Query(
        None, min_length=1, description="Search term (Title, Content, or Category)"
    ),
    category_id: Optional[UUID] = Query(None, description="Filter by Category ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db),
):
    """
    Get resources with optional Search (q) and Filtering (category_id).
    Pagination included.
    """
    try:
        resources, total = ResourceService.get_resources(
            session=session,
            page=page,
            limit=limit,
            query_str=q,
            category_id=category_id,
        )

        total_pages = math.ceil(total / limit) if limit > 0 else 0

        return {
            "status": "success",
            "message": "Resources retrieved successfully",
            "data": resources,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Error retrieving resources: {str(e)}", exc_info=True)
        return fail_response(message="Failed to fetch resources", status_code=500)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_resource(
    schema: ResourceCreate,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new resource (article/video content)."""
    try:
        resource = ResourceService.create_resource(session, schema)
        return success_response(
            message="Resource created successfully",
            status_code=201,
            data={
                "id": resource.id,
                "title": resource.title,
                "category_id": resource.category_id,
                "created_at": resource.created_at,
            },
        )
    except HTTPException as e:
        logger.error(
            f"HTTP error creating resource {e.status_code}: {str(e)}", exc_info=True
        )
        return fail_response(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error creating resource: {str(e)}", exc_info=True)
        return fail_response(message="Failed to create resource", status_code=500)


@router.get("/{resource_id}", status_code=status.HTTP_200_OK)
async def get_resource_by_id(resource_id: UUID, session: Session = Depends(get_db)):
    """Get a single resource by ID."""
    try:
        resource = ResourceService.get_resource_by_id(session, resource_id)
        return success_response(
            message="Resource retrieved successfully",
            status_code=200,
            data={
                "id": resource.id,
                "title": resource.title,
                "content": resource.content,
                "category_id": resource.category_id,
                "created_at": resource.created_at,
                "updated_at": resource.updated_at,
            },
        )
    except HTTPException as e:
        logger.error(
            f"HTTP error retrieving resource {e.status_code}: {str(e)}", exc_info=True
        )
        return fail_response(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error retrieving resource: {str(e)}", exc_info=True)
        return fail_response(message="Failed to retrieve resource", status_code=500)


@router.patch("/{resource_id}", status_code=status.HTTP_200_OK)
async def update_resource(
    resource_id: UUID,
    schema: ResourceUpdate,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update a resource by ID."""
    try:
        resource = ResourceService.update_resource(session, resource_id, schema)
        return success_response(
            message="Resource updated successfully",
            status_code=200,
            data={
                "id": resource.id,
                "title": resource.title,
                "category_id": resource.category_id,
                "created_at": resource.created_at,
                "updated_at": resource.updated_at,
            },
        )
    except HTTPException as e:
        logger.error(
            f"HTTP error updating resource {e.status_code}: {str(e)}", exc_info=True
        )
        return fail_response(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error updating resource: {str(e)}", exc_info=True)
        return fail_response(message="Failed to update resource", status_code=500)


@router.delete("/{resource_id}", status_code=status.HTTP_200_OK)
async def delete_resource(
    resource_id: UUID,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a resource by ID."""
    try:
        ResourceService.delete_resource(session, resource_id)
        return success_response(
            message="Resource deleted successfully", status_code=200, data=None
        )
    except HTTPException as e:
        logger.error(
            f"HTTP error deleting resource {e.status_code}: {str(e)}", exc_info=True
        )
        return fail_response(message=e.detail, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error deleting resource: {str(e)}", exc_info=True)
        return fail_response(message="Failed to delete resource", status_code=500)

"""
This module contains the API endpoints for admin-related operations.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.v1.routes.deps import require_super_admin
from api.v1.schemas.admin import AdminCreate
from api.v1.services.admin_service import create_admin
from api.utils.responses import fail_response, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_admin(
    payload: AdminCreate,
    db: Session = Depends(get_db),
    _super_admin=Depends(require_super_admin),  # ensures only super_admin can call
) -> Any:
    """
    Register a new admin. Only callable by an authenticated super_admin.
    """
    user, error = create_admin(db=db, admin_in=payload)

    if error:
        logger.warning("Admin registration failed: %s", error)
        return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)

    # Prepare safe user data (exclude password_hash)
    admin_data = {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
    }

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Admin account created successfully.",
        data={"admin": admin_data},
    )


"""
This module contains dependency-related functions for the routes.
"""

from fastapi import Depends, HTTPException, status

from api.v1.models.user.user import User
from api.utils.deps import get_current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Ensures current_user is a super_admin. If not, raise 403.
    This wrapper depends on `get_current_user` (which must be implemented by auth teamate).
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
        )
    if getattr(current_user, "role", None) != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can perform this action.",
        )
    return current_user

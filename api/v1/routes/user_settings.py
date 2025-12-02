"""
This module contains the API endpoints for managing user settings.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.utils.deps import get_current_user
from api.v1.models.user.user import User
from api.v1.schemas.user_settings import (
    UserSettingsUpdate,
    UserProfileUpdate,
    NotificationPreferencesUpdate,
    AppSettingsUpdate,
    PasswordUpdate,
)
from api.v1.services.user_settings_services import (
    get_user_settings,
    update_user_profile,
    update_notification_preferences,
    update_app_settings,
    update_password,
)
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger

router = APIRouter(prefix="/user", tags=["User Settings"])


@router.get("/settings", status_code=status.HTTP_200_OK)
async def get_settings(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user settings including profile, notifications, and app preferences"""
    logger.info("Fetching settings for user: %s", current_user.email)

    settings = get_user_settings(db, current_user.id)

    if not settings:
        logger.warning("Settings not found for user: %s", current_user.id)
        return fail_response(
            status_code=status.HTTP_404_NOT_FOUND, message="User settings not found"
        )

    logger.info("Settings retrieved successfully for user: %s", current_user.email)
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Settings retrieved successfully",
        data=settings,
    )


@router.put("/settings", status_code=status.HTTP_200_OK)
async def update_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user settings (profile, notifications, and/or app settings)"""
    logger.info("Updating settings for user: %s", current_user.email)

    updated_data = None

    if settings_update.profile:
        data, error = update_user_profile(db, current_user.id, settings_update.profile)
        if error:
            logger.warning(
                "Profile update failed for user %s: %s", current_user.email, error
            )
            return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)
        updated_data = data

    if settings_update.notifications:
        data, error = update_notification_preferences(
            db, current_user.id, settings_update.notifications
        )
        if error:
            logger.warning(
                "Notification update failed for user %s: %s", current_user.email, error
            )
            return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)
        updated_data = data

    if settings_update.app_settings:
        data, error = update_app_settings(
            db, current_user.id, settings_update.app_settings
        )
        if error:
            logger.warning(
                "App settings update failed for user %s: %s", current_user.email, error
            )
            return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)
        updated_data = data

    if not updated_data:
        updated_data = get_user_settings(db, current_user.id)

    logger.info("Settings updated successfully for user: %s", current_user.email)
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Settings updated successfully",
        data=updated_data,
    )


@router.put("/settings/profile", status_code=status.HTTP_200_OK)
async def update_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user profile information"""
    logger.info("Updating profile for user: %s", current_user.email)

    data, error = update_user_profile(db, current_user.id, profile_update)

    if error:
        logger.warning(
            "Profile update failed for user %s: %s", current_user.email, error
        )
        return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)

    logger.info("Profile updated successfully for user: %s", current_user.email)
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Profile updated successfully",
        data=data,
    )


@router.put("/settings/notifications", status_code=status.HTTP_200_OK)
async def update_notifications(
    notification_update: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update notification preferences"""
    logger.info("Updating notification preferences for user: %s", current_user.email)

    data, error = update_notification_preferences(
        db, current_user.id, notification_update
    )

    if error:
        logger.warning(
            "Notification update failed for user %s: %s", current_user.email, error
        )
        return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)

    logger.info(
        "Notification preferences updated successfully for user: %s", current_user.email
    )
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Notification preferences updated successfully",
        data=data,
    )


@router.put("/settings/app", status_code=status.HTTP_200_OK)
async def update_app_settings_route(
    app_settings_update: AppSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update app settings"""
    logger.info("Updating app settings for user: %s", current_user.email)

    data, error = update_app_settings(db, current_user.id, app_settings_update)

    if error:
        logger.warning(
            "App settings update failed for user %s: %s", current_user.email, error
        )
        return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)

    logger.info("App settings updated successfully for user: %s", current_user.email)
    return success_response(
        status_code=status.HTTP_200_OK,
        message="App settings updated successfully",
        data=data,
    )


@router.put("/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_update: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change user password"""
    logger.info("Password change request for user: %s", current_user.email)

    success, error = update_password(db, current_user.id, password_update)

    if not success:
        logger.warning(
            "Password change failed for user %s: %s", current_user.email, error
        )
        return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)

    logger.info("Password changed successfully for user: %s", current_user.email)
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Password updated successfully",
        data={"password_changed": True},
    )

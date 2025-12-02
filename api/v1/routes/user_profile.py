from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.v1.models.user.user import User, UserProfile
from api.v1.schemas.profile_setup import (
    ProfileSetupSubmit,
    ProfileSetupResponse,
    ProfileSetupUpdate,
)
from api.v1.services.profile_setup import ProfileSetupService, ProfileSetupExistsError
from api.utils.deps import get_current_user
from api.utils.responses import success_response, fail_response
from api.utils.logger import logger

router = APIRouter(prefix="/profile", tags=["Profile"])
old_profile_router1 = APIRouter(tags=["Profile"])
old_profile_router2 = APIRouter(tags=["Authentication"])

@router.get("/", status_code=status.HTTP_200_OK)
def get_user_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Retrieve the authenticated user's profile information.
    """

    logger.info(f"Fetching profile for user_id={current_user.id}")

    profile = UserProfile.fetch_one(db, user_id=current_user.id)

    profile_data = {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "phone": current_user.phone,
        "phone_verified": current_user.phone_verified,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "last_login_at": current_user.last_login_at,
        "profile": {
            "date_of_birth": profile.date_of_birth if profile else None,
            "state": profile.state if profile else None,
            "country": profile.country if profile else None,
            "occupation": profile.occupation if profile else None,
            "tech_savviness": profile.tech_savviness if profile else None,
            "preferred_language": profile.preferred_language if profile else None,
            "ai_tone_preference": profile.ai_tone_preference if profile else None,
            "onboarding_stage": profile.onboarding_stage if profile else None,
            "onboarding_completed": profile.onboarding_completed if profile else None,
            "onboarding_completed_at": (
                profile.onboarding_completed_at if profile else None
            ),
            "push_notifications_enabled": (
                profile.push_notifications_enabled if profile else None
            ),
            "email_notifications_enabled": (
                profile.email_notifications_enabled if profile else None
            ),
            "sms_notifications_enabled": (
                profile.sms_notifications_enabled if profile else None
            ),
            "timezone": profile.timezone if profile else None,
            "avatar_url": profile.avatar_url if profile else None,
            "bio": profile.bio if profile else None,
        },
    }

    logger.info(f"Successfully fetched profile for user_id={current_user.id}")

    return success_response(
        status_code=status.HTTP_200_OK,
        message="User profile fetched successfully",
        data=profile_data,
    )


@old_profile_router2.get("/auth/profile", status_code=status.HTTP_200_OK)
def get_user_profile_alias(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Alias for retrieving the authenticated user's profile information via /auth/profile.
    """
    return get_user_profile(db, current_user)


@router.get("/setup", status_code=status.HTTP_200_OK)
def get_profile_setup(
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get the current user's profile setup details.
    """
    logger.info(f"Get profile setup request by {current_user.id}")

    profile = ProfileSetupService.get(session, current_user.id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile setup not found"
        )
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Profile setup retrieved successfully",
        data=profile,
    )


@old_profile_router1.get("/profile-setup", status_code=status.HTTP_200_OK)
def get_profile_setup_alias(
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Alias for getting the current user's profile setup details via /profile-setup.
    """
    return get_profile_setup(session, current_user)


@router.post("/setup", status_code=status.HTTP_201_CREATED)
def create_profile_setup(
    payload: ProfileSetupSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new profile setup for the authenticated user.
    """

    logger.info(f"Creating profile setup | user_id={current_user.id}")

    try:
        service = ProfileSetupService()

        profile = service.create(
            session=db,
            user_id=current_user.id,
            payload=payload,
        )

        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Profile setup created successfully",
            data=profile,
        )

    except ProfileSetupExistsError as e:
        logger.info(f"Profile setup already exists for user {current_user.id}")

        return fail_response(
            status_code=status.HTTP_409_CONFLICT,
            message=str(e),
            context={"detail": str(e)},
        )

    except SQLAlchemyError as db_err:
        logger.error(
            f"[DB ERROR] creating profile setup for user {current_user.id}: {db_err}"
        )

        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Database error occurred while creating profile setup",
            context={"error": str(db_err)},
        )

    except Exception as e:
        logger.error(
            f"[UNEXPECTED ERROR] creating profile setup for user {current_user.id}: {e}"
        )

        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            context={"error": str(e)},
        )


@old_profile_router1.post("/profile-setup", status_code=status.HTTP_201_CREATED)
def create_profile_setup_alias(
    payload: ProfileSetupSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Alias for creating a new profile setup for the authenticated user via /profile-setup.
    """
    return create_profile_setup(payload, db, current_user)


@router.patch(
    "/setup", status_code=status.HTTP_200_OK, response_model=ProfileSetupResponse
)
def update_profile_setup(
    payload: ProfileSetupUpdate,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Partially update the user's profile setup.
    Only fields provided in the request body will be updated.
    """
    try:
        updated_profile = ProfileSetupService.update(
            session=session, user_id=current_user.id, payload=payload
        )

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Profile updated successfully",
            data=ProfileSetupService.build_profile(session, updated_profile),
        )
    except HTTPException as e:
        return fail_response(
            status_code=e.status_code, message=e.detail, context={"detail": e.detail}
        )
    except Exception as e:
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update profile",
            context={"detail": str(e)},
        )


@old_profile_router1.patch(
    "/profile-setup", status_code=status.HTTP_200_OK, response_model=ProfileSetupResponse
)
def update_profile_setup_alias(
    payload: ProfileSetupUpdate,
    session: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Alias for partially updating the user's profile setup via /profile-setup.
    """
    return update_profile_setup(payload, session, current_user)
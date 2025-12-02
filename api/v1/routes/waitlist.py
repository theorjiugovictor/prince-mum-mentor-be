
"""
This module contains the API endpoints for managing the waitlist.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from api.v1.schemas.waitlist import WaitlistCreate
from api.v1.services.waitlist import create_waitlist_entry, delete_waitlist_entry
from api.v1.services.email_services import send_email
from api.db.database import get_db
from api.utils.responses import success_response, fail_response
from api.utils.deps import get_admin_user
from api.v1.models.user.user import User

router = APIRouter(tags=["Waitlist"])


@router.post("/waitlist", status_code=status.HTTP_201_CREATED)
async def join_waitlist(data: WaitlistCreate, db: Session = Depends(get_db)):
    """
    Adds a new user to the waitlist.
    """
    new_entry, existing_entry = create_waitlist_entry(db, data)

    if existing_entry:
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Email already registered on waitlist",
            data={
                "id": str(existing_entry.id),
                "full_name": existing_entry.full_name,
                "email": existing_entry.email,
                # "source": existing_entry.referral_source,
                "joined_at": existing_entry.joined_at.isoformat() + "Z",
            },
        )

    if new_entry is None:
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create waitlist entry",
        )

    # Send welcome email with user's name
    subject = "Welcome to Mum Mentor Waitlist!"
    body = f"""Hi {new_entry.full_name},
You've officially secured your spot on the Nora waitlist, and we're so excited to have you here! You're one step closer to experiencing a new kind of support made just for mums like you.
Soon, Nora will be right at your fingertips - ready to help you navigate motherhood with calm, clarity, and confidence. From trusted answers to personalised guidance, your journey is about to get a whole lot lighter.
Psst… keep an eye on your inbox - we're working on something truly special behind the scenes. The wait's almost over, and trust us, it's going to be worth it. Your motherhood experience is about to feel a lot more supported.
Feeling the love?
 Share Nora with another mum who'd appreciate a little extra support.
 And don't miss out on the early peeks and update.
Welcome to Nora — we're so happy you're here."""

    await send_email(new_entry.email, subject, body)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Successfully joined the waitlist",
        data={
            "id": str(new_entry.id),
            "full_name": new_entry.full_name,
            "email": new_entry.email,
            # "source": new_entry.referral_source,
            "joined_at": new_entry.joined_at.isoformat() + "Z",
        },
    )


@router.delete("/waitlist/{waitlist_id}", status_code=status.HTTP_200_OK)
async def delete_waitlist_user(
    waitlist_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """
    Admin endpoint to delete a waitlist entry.
    Only authorized admin users can perform this action.

    Args:
        waitlist_id: UUID of the waitlist entry to delete
        db: Database session

    Returns:
        Success response with deleted entry details or error message
    """
    deleted_entry, error = delete_waitlist_entry(db, waitlist_id)

    if error:
        if error == "Waitlist entry not found":
            return fail_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=error,
            )
        if error == "Invalid waitlist ID format":
            return fail_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=error,
            )
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error,
        )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Waitlist entry deleted successfully",
        data={
            "id": str(deleted_entry.id),
            "full_name": deleted_entry.full_name,
            "email": deleted_entry.email,
            "joined_at": deleted_entry.joined_at.isoformat() + "Z",
        },
    )

from typing import Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from api.v1.models.user.user import (
    User, UserProfile, UserSettings, 
    UserAuthSession, UserOTPVerification, 
    EmailVerificationToken, UserActivityLog)
from api.utils.security import verify_password
from api.utils.logger import logger

class AccountService:
    """Service class for account management operations"""

    @staticmethod
    def delete_user_account(
        db: Session,
        user_id: str,
        password: str,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Permanently delete user account and all associated data
        
        Args:
            db: Database session
            user_id: User ID to delete
            password: User password for confirmation
            reason: Optional reason for account deletion
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Fetch user
            user = User.fetch_unique(db, id=user_id)
            if not user:
                logger.warning("Account deletion attempt for non-existent user: %s", user_id)
                return False, "User not found"

            # Verify password
            if not verify_password(password, user.password_hash):
                logger.warning("Invalid password during account deletion attempt for user: %s", user_id)
                return False, "Invalid password"

            # Check if account is already deleted
            if user.is_deleted:
                logger.warning("Account deletion attempt for already deleted user: %s", user_id)
                return False, "Account already deleted"

            # Perform deletion in transaction
            return AccountService._delete_user_data(db, user, reason)

        except Exception as e:
            db.rollback()
            logger.error(
                "Error during account deletion for user %s: %s",
                user_id,
                str(e),
                exc_info=True
            )
            return False, "An error occurred during account deletion"

    @staticmethod
    def _delete_user_data(db: Session, user: User, reason: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Delete all user data in transaction"""
        try:
            deletion_time = datetime.now(timezone.utc)

            # Log deletion activity with reason if provided
            activity_metadata = {
                "status": "account_deleted",
                "deletion_time": deletion_time.isoformat()
            }
            if reason:
                activity_metadata["deletion_reason"] = reason
            
            # Create activity log before deleting other data
            deletion_log = UserActivityLog(
                user_id=user.id,
                activity_type="account_deletion",
                activity_metadata=activity_metadata
            )
            deletion_log.insert(db)

            # 1. Delete related records
            AccountService._delete_user_related_data(db, user.id)

            # 2. Soft delete user account (mark as deleted)
            user.is_deleted = True
            user.deleted_at = deletion_time
            user.is_active = False
            user.email = f"deleted_{user.id}@deleted.com"
            user.phone = None
            user.password_hash = "deleted"
            user.google_id = None
            user.full_name = "Deleted User"
            
            user.update(db)

            logger.info(
                "Account successfully deleted for user: %s%s",
                user.id,
                f" (Reason: {reason})" if reason else ""
            )
            return True, None

        except Exception as e:
            db.rollback()
            logger.error(
                "Error deleting user data for %s: %s",
                user.id,
                str(e),
                exc_info=True
            )
            return False, "Failed to delete user data"

    @staticmethod
    def _delete_user_related_data(db: Session, user_id: str) -> None:
        """Delete all user-related data"""
        # Delete user profile
        profile = UserProfile.fetch_unique(db, user_id=user_id)
        if profile:
            profile.delete(db)

        # Delete user settings
        settings = UserSettings.fetch_unique(db, user_id=user_id)
        if settings:
            settings.delete(db)

        # Delete auth sessions
        sessions = UserAuthSession.fetch_all(db, user_id=user_id)
        for session in sessions:
            session.delete(db)

        # Delete OTP records
        otp_records = UserOTPVerification.fetch_all(db, user_id=user_id)
        for otp in otp_records:
            otp.delete(db)

        # Delete verification tokens
        verification_tokens = EmailVerificationToken.fetch_all(db, user_id=user_id)
        for token in verification_tokens:
            token.delete(db)

        # Note: UserActivityLog records are kept for audit purposes

        logger.info("Deleted all related data for user: %s", user_id)
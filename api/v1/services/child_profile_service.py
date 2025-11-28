"""
Service layer for child profile operations.
"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from api.v1.models.user.user import ChildProfile, ProfileSetup
from api.v1.schemas.child_profile import (
    CreateChildProfileRequest,
    UpdateChildProfileRequest,
    ChildProfileResponse,
)
from api.utils.logger import logger


class ChildProfileService:
    """Service for managing child profiles."""

    @staticmethod
    def _calculate_age(date_of_birth: Optional[date]) -> Optional[int]:
        """Calculate age from date of birth."""
        if not date_of_birth:
            return None
        
        today = date.today()
        age = today.year - date_of_birth.year
        
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
            
        return age if age >= 0 else None

    @staticmethod
    def _build_response(child: ChildProfile) -> dict:
        """Build response dictionary from ChildProfile model."""
        return {
            "id": child.id,
            "profile_setup_id": child.profile_setup_id,
            "full_name": child.full_name,
            "date_of_birth": child.date_of_birth,
            "due_date": child.due_date,
            "gender": child.gender,
            "birth_order": child.birth_order,
            "profile_picture_url": child.profile_picture_url,
            "age": ChildProfileService._calculate_age(child.date_of_birth),
            "created_at": child.created_at,
            "updated_at": child.updated_at,
        }

    @staticmethod
    def _verify_ownership(db: Session, profile_setup_id: UUID, user_id: UUID) -> ProfileSetup:
        """Verify that the profile setup belongs to the user."""
        profile_setup = db.scalar(
            select(ProfileSetup).where(
                ProfileSetup.id == profile_setup_id,
                ProfileSetup.user_id == user_id
            )
        )
        
        if not profile_setup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile setup not found or does not belong to you"
            )
        
        return profile_setup

    @staticmethod
    def create_child_profile(
        db: Session,
        user_id: UUID,
        request: CreateChildProfileRequest
    ) -> dict:
        """Create a new child profile."""
        try:
            # Verify ownership
            ChildProfileService._verify_ownership(db, request.profile_setup_id, user_id)
            
            # Create child profile
            child = ChildProfile(
                profile_setup_id=request.profile_setup_id,
                full_name=request.full_name.strip(),
                date_of_birth=request.date_of_birth,
                due_date=request.due_date,
                gender=request.gender,
                birth_order=request.birth_order,
                profile_picture_url=request.profile_picture_url,
            )
            
            db.add(child)
            db.commit()
            db.refresh(child)
            
            logger.info(f"Child profile created: {child.id} for user {user_id}")
            
            return ChildProfileService._build_response(child)
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating child profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while creating child profile"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error creating child profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred"
            )

    @staticmethod
    def get_child_profile(db: Session, child_id: UUID, user_id: UUID) -> Optional[dict]:
        """Get a single child profile by ID."""
        try:
            # Get child profile with profile setup
            child = db.scalar(
                select(ChildProfile).where(ChildProfile.id == child_id)
            )
            
            if not child:
                return None
            
            # Verify ownership through profile setup
            ChildProfileService._verify_ownership(db, child.profile_setup_id, user_id)
            
            return ChildProfileService._build_response(child)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving child profile {child_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving child profile"
            )

    @staticmethod
    def get_all_child_profiles(db: Session, user_id: UUID) -> List[dict]:
        """Get all child profiles for a user."""
        try:
            # Get user's profile setup
            profile_setup = db.scalar(
                select(ProfileSetup).where(ProfileSetup.user_id == user_id)
            )
            
            if not profile_setup:
                return []
            
            # Get all children
            children = db.scalars(
                select(ChildProfile).where(
                    ChildProfile.profile_setup_id == profile_setup.id
                )
            ).all()
            
            return [ChildProfileService._build_response(child) for child in children]
            
        except Exception as e:
            logger.error(f"Error retrieving child profiles for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving child profiles"
            )

    @staticmethod
    def update_child_profile(
        db: Session,
        child_id: UUID,
        user_id: UUID,
        request: UpdateChildProfileRequest
    ) -> dict:
        """Update a child profile."""
        try:
            # Get child profile
            child = db.scalar(
                select(ChildProfile).where(ChildProfile.id == child_id)
            )
            
            if not child:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Child profile not found"
                )
            
            # Verify ownership
            ChildProfileService._verify_ownership(db, child.profile_setup_id, user_id)
            
            # Apply updates
            update_data = request.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                if field == "full_name" and value:
                    setattr(child, field, value.strip())
                else:
                    setattr(child, field, value)
            
            db.commit()
            db.refresh(child)
            
            logger.info(f"Child profile updated: {child.id} for user {user_id}")
            
            return ChildProfileService._build_response(child)
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating child profile {child_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while updating child profile"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error updating child profile {child_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred"
            )

    @staticmethod
    def delete_child_profile(db: Session, child_id: UUID, user_id: UUID) -> bool:
        """Delete a child profile."""
        try:
            # Get child profile
            child = db.scalar(
                select(ChildProfile).where(ChildProfile.id == child_id)
            )
            
            if not child:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Child profile not found"
                )
            
            # Verify ownership
            ChildProfileService._verify_ownership(db, child.profile_setup_id, user_id)
            
            # Delete
            db.delete(child)
            db.commit()
            
            logger.info(f"Child profile deleted: {child_id} for user {user_id}")
            
            return True
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error deleting child profile {child_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while deleting child profile"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error deleting child profile {child_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred"
            )

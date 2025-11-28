from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional
import uuid

from api.v1.models.milestones import Milestone, MotherCategory, ChildCategory
from api.v1.models.user.user import ChildProfile, ProfileSetup
from api.v1.schemas.milestone import MilestoneCreate, MilestoneToggle, MilestoneUpdate

class MilestoneService:

    @staticmethod
    def _validate_child_ownership(session: Session, user_id: uuid.UUID, child_id: uuid.UUID):
        """
        Security Check: Ensure the child exists AND belongs to the requesting mother.
        """
        # We join tables to find the child linked to this specific user_id
        child = session.query(ChildProfile).join(ProfileSetup).filter(
            ChildProfile.id == child_id,
            ProfileSetup.user_id == user_id
        ).first()

        if not child:
            raise HTTPException(
                status_code=404, 
                detail="Child profile not found or does not belong to you."
            )
        return child

    @staticmethod
    def _validate_category_for_owner_type(category: str, owner_type: str):
        """
        Validate that the category matches the owner type.
        Mother categories: Body Recovery, Mental Wellness, Routine Builder, Self Care
        Child categories: Development, Health and Nutrition, Activities and Play, Growth Check
        """
        mother_categories = [cat.value for cat in MotherCategory]
        child_categories = [cat.value for cat in ChildCategory]
        
        if owner_type == "mother":
            if category not in mother_categories:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category for mother. Must be one of: {', '.join(mother_categories)}"
                )
        elif owner_type == "child":
            if category not in child_categories:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category for child. Must be one of: {', '.join(child_categories)}"
                )

    @staticmethod
    def create(session: Session, user_id: uuid.UUID, payload: MilestoneCreate) -> Milestone:
        if payload.child_id:
            MilestoneService._validate_child_ownership(session, user_id, payload.child_id)
            
            owner_id = payload.child_id
            owner_type = "child"
        else:
            owner_id = user_id
            owner_type = "mother"

        # Validate category matches owner type
        MilestoneService._validate_category_for_owner_type(payload.category, owner_type)

        new_milestone = Milestone(
            owner_id=owner_id,
            owner_type=owner_type,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            status="pending"
        )

        session.add(new_milestone)
        try:
            session.commit()
            session.refresh(new_milestone)
            return new_milestone
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=400, detail=f"Database Error: {str(e)}")

    @staticmethod
    def toggle_status(session: Session, user_id: uuid.UUID, milestone_id: uuid.UUID, payload: MilestoneToggle) -> Milestone:
        milestone = session.query(Milestone).filter(Milestone.id == milestone_id).first()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        if milestone.owner_type == "child":
            MilestoneService._validate_child_ownership(session, user_id, milestone.owner_id)
        elif milestone.owner_type == "mother":
            if milestone.owner_id != user_id:
                raise HTTPException(status_code=403, detail="Not authorized")

        milestone.status = "completed" if payload.completed else "pending"
        
        session.commit()
        session.refresh(milestone)
        return milestone

    @staticmethod
    def get_pending(session: Session, user_id: uuid.UUID, child_id: Optional[uuid.UUID] = None):
        if child_id:
            MilestoneService._validate_child_ownership(session, user_id, child_id)
            target_id = child_id
            target_type = "child"
        else:
            target_id = user_id
            target_type = "mother"

        return session.query(Milestone).filter(
            Milestone.owner_id == target_id,
            Milestone.owner_type == target_type,
            Milestone.status == "pending"
        ).order_by(Milestone.created_at.asc()).all()

    @staticmethod
    def get_all(session: Session, user_id: uuid.UUID, child_id: Optional[uuid.UUID] = None, category: Optional[str] = None):
        """Get all milestones with optional category filter."""
        if child_id:
            MilestoneService._validate_child_ownership(session, user_id, child_id)
            target_id = child_id
            target_type = "child"
        else:
            target_id = user_id
            target_type = "mother"

        query = session.query(Milestone).filter(
            Milestone.owner_id == target_id,
            Milestone.owner_type == target_type
        )

        if category:
            # Validate category matches the owner type
            MilestoneService._validate_category_for_owner_type(category, target_type)
            query = query.filter(Milestone.category == category)

        return query.order_by(Milestone.created_at.desc()).all()

    @staticmethod
    def update(session: Session, user_id: uuid.UUID, milestone_id: uuid.UUID, payload: MilestoneUpdate) -> Milestone:
        """
        Update a milestone's details.
        Only the milestone owner can update it.
        """
        milestone = session.query(Milestone).filter(Milestone.id == milestone_id).first()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        # Validate ownership
        if milestone.owner_type == "child":
            MilestoneService._validate_child_ownership(session, user_id, milestone.owner_id)
        elif milestone.owner_type == "mother":
            if milestone.owner_id != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to update this milestone")

        # Update fields if provided
        if payload.name is not None:
            milestone.name = payload.name
        if payload.description is not None:
            milestone.description = payload.description
        if payload.category is not None:
            # Validate new category matches owner type
            MilestoneService._validate_category_for_owner_type(payload.category, milestone.owner_type)
            milestone.category = payload.category

        try:
            session.commit()
            session.refresh(milestone)
            return milestone
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=400, detail=f"Database Error: {str(e)}")

    @staticmethod
    def delete(session: Session, user_id: uuid.UUID, milestone_id: uuid.UUID) -> None:
        """
        Delete a milestone.
        Only the milestone owner can delete it.
        """
        milestone = session.query(Milestone).filter(Milestone.id == milestone_id).first()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        # Validate ownership
        if milestone.owner_type == "child":
            MilestoneService._validate_child_ownership(session, user_id, milestone.owner_id)
        elif milestone.owner_type == "mother":
            if milestone.owner_id != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this milestone")

        try:
            session.delete(milestone)
            session.commit()
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=400, detail=f"Database Error: {str(e)}")

    @staticmethod
    def get_progress(session: Session, user_id: uuid.UUID, child_id: Optional[uuid.UUID] = None) -> dict:
        """
        Get overall milestone progress statistics.
        Returns count of pending and completed milestones.
        """
        if child_id:
            MilestoneService._validate_child_ownership(session, user_id, child_id)
            target_id = child_id
            target_type = "child"
        else:
            target_id = user_id
            target_type = "mother"

        # Count pending milestones
        pending_count = session.query(Milestone).filter(
            Milestone.owner_id == target_id,
            Milestone.owner_type == target_type,
            Milestone.status == "pending"
        ).count()

        # Count completed milestones
        completed_count = session.query(Milestone).filter(
            Milestone.owner_id == target_id,
            Milestone.owner_type == target_type,
            Milestone.status == "completed"
        ).count()

        return {
            "pending_milestones": pending_count,
            "completed_milestones": completed_count
        }
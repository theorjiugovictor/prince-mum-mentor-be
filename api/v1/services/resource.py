from sqlalchemy import desc, or_,  select
from sqlalchemy.orm import Session, joinedload
from typing import Tuple, List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from api.utils.logger import logger
from api.v1.models.resource.resource import Resource
from api.v1.models.resource.resource_category import ResourceCategory
from api.v1.schemas.resource import (
    ResourceCreate, CategoryCreate, ResourceUpdate
)


class ResourceService:

    @staticmethod
    def get_resources(
        session: Session,
        page: int,
        limit: int,
        query_str: Optional[str] = None,
        category_id: Optional[UUID] = None
    ) -> Tuple[List[Resource], int]:
        """
        Unified method to fetch resources.
        Handles: Pagination, Sorting, Search (Title/Content/CategoryName),
        and Category Filtering.
        """
        skip = (page - 1) * limit
        logger.info(
            f"Fetching resources. Page={page}, Limit={limit}, "
            f"Q='{query_str}', CatID={category_id}"
        )

        # 1. Base Query with Eager Loading
        query = session.query(Resource).options(
            joinedload(Resource.category),
            joinedload(Resource.media)
        )

        # 2. Join Category (Required for filtering/searching by category name)
        query = query.join(Resource.category)

        # 3. Apply Search Logic (if 'q' is provided)
        if query_str:
            search_filter = or_(
                Resource.title.ilike(f"%{query_str}%"),
                Resource.content.ilike(f"%{query_str}%"),
                ResourceCategory.name.ilike(f"%{query_str}%")
            )
            query = query.filter(search_filter)

        # 4. Apply Category Filter (if 'category_id' is provided)
        if category_id:
            query = query.filter(Resource.category_id == category_id)

        # 5. Execute Count and Fetch
        total = query.count()
        resources = query.order_by(
            desc(Resource.created_at)
        ).offset(skip).limit(limit).all()

        return resources, total

    @staticmethod
    def search_by_title(
        session: Session,
        title: str,
        page: int,
        limit: int
    ):
        """
        Search resources by partial + case-insensitive title match.
        """

        # Paginated query
        stmt = (
            select(Resource)
            .where(Resource.title.ilike(f"%{title}%"))
            .offset((page - 1) * limit)
            .limit(limit)
        )
        resources = session.scalars(stmt).all()

        # Total count
        count_stmt = select(Resource).where(Resource.title.ilike(f"%{title}%"))
        total = len(session.scalars(count_stmt).all())

        return resources, total

    @staticmethod
    def create_resource(session: Session, schema: ResourceCreate) -> Resource:
        category = ResourceCategory.fetch_one(session, id=schema.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource Category not found"
            )

        new_resource = Resource(
            title=schema.title,
            content=schema.content,
            category_id=schema.category_id
        )
        return new_resource.insert(session)

    @staticmethod
    def get_resource_by_id(session: Session, resource_id: UUID) -> Resource:
        resource = Resource.fetch_one(session, id=resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        return resource

    @staticmethod
    def update_resource(
        session: Session, resource_id: UUID, schema: ResourceUpdate
    ) -> Resource:
        resource = Resource.fetch_one(session, id=resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )

        resource.title = schema.title
        resource.content = schema.content
        session.commit()
        session.refresh(resource)
        return resource

    @staticmethod
    def delete_resource(session: Session, resource_id: UUID) -> None:
        resource = Resource.fetch_one(session, id=resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        resource.delete(session)

    # --- CRUD: CATEGORIES ---

    @staticmethod
    def create_category(
        session: Session, schema: CategoryCreate
    ) -> ResourceCategory:
        existing_cat = ResourceCategory.fetch_one(session, name=schema.name)
        if existing_cat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{schema.name}' already exists"
            )
        new_category = ResourceCategory(name=schema.name)
        return new_category.insert(session)

    @staticmethod
    def get_all_categories(session: Session) -> List[ResourceCategory]:
        return session.query(ResourceCategory).all()

    @staticmethod
    def get_category_by_id(
        session: Session, category_id: UUID
    ) -> ResourceCategory:
        category = ResourceCategory.fetch_one(session, id=category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource Category not found"
            )
        return category

    @staticmethod
    def update_category(
        session: Session, category_id: UUID, schema: CategoryCreate
    ) -> ResourceCategory:
        category = ResourceCategory.fetch_one(session, id=category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource Category not found"
            )

        # Check unique name constraint (excluding current category)
        existing_cat = ResourceCategory.fetch_one(session, name=schema.name)
        if existing_cat and existing_cat.id != category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{schema.name}' already exists"
            )

        category.name = schema.name
        session.commit()
        session.refresh(category)
        return category

    @staticmethod
    def delete_category(session: Session, category_id: UUID) -> None:
        category = ResourceCategory.fetch_one(session, id=category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource Category not found"
            )
        category.delete(session)

from typing import Optional, Tuple, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import and_, or_, Integer
import json
from fastapi import UploadFile, Request
from sqlalchemy.orm import Session, subqueryload, joinedload
from sqlalchemy import desc, asc
from sqlalchemy import func, select
from api.v1.models.community.post_likes import PostLike
from api.v1.models.community.post_comments import PostComment 
from sqlalchemy.exc import SQLAlchemyError

from api.utils.logger import logger
from api.v1.models.community.posts import Post
from api.v1.models.community.post_photos import PostPhoto
from api.v1.models.photos import Photos
from api.v1.schemas.community_posts import PostCreateRequest


class CommunityPostService:
    def __init__(self, db: Session):
        self.db = db

    def create_post(
    self, *, user_id: UUID, payload: PostCreateRequest
) -> Tuple[Optional[Post], Optional[Tuple[int, str]]]:
        """Create post with existing photo IDs (JSON)"""
        try:
            # Validate photo IDs if provided
            if payload.photo_ids:
                is_valid, error_message = self._validate_photo_ids(payload.photo_ids)
                if not is_valid:
                    return None, (400, error_message)
            
            # Create the post
            post = Post(
                user_id=user_id, 
                title=payload.title, 
                content=payload.content
            )
            
            post.insert(self.db, commit=False)
            
            # Add photos if provided
            if payload.photo_ids:
                for photo_id in payload.photo_ids:
                    photo = Photos.fetch_one(self.db, id=photo_id)
                    if not photo:
                        self.db.rollback()
                        return None, (404, f"Photo with ID {photo_id} not found")
                    
                    post_photo = PostPhoto(
                        post_id=post.id,
                        url=photo.image_url
                    )
                    post_photo.add(self.db)
            
            self.db.commit()
            
            try:
                self.db.refresh(post)
                # Set initial counts for new post
                post.likes_count = 0
                post.comments_count = 0
            except Exception as exc_refresh:
                logger.warning(
                    "Failed to refresh post after creation | post_id=%s | user_id=%s | error=%s",
                    getattr(post, "id", None),
                    user_id,
                    exc_refresh,
                )

            logger.info(
                "Community post created | post_id=%s | user_id=%s | photo_count=%s", 
                post.id, 
                user_id,
                len(payload.photo_ids) if payload.photo_ids else 0
            )
            return post, None

        except Exception as exc:  
            logger.error(
                "Error creating community post | user_id=%s | title=%s | error=%s",
                user_id,
                payload.title,
                exc,
            )
            self.db.rollback()
            return None, (500, "Failed to create post")

    def delete_post(self, *, post_id: UUID, user_id: UUID) -> Tuple[bool, Optional[Tuple[int, str]]]:
        """Delete a community post if it belongs to the given user.

        Returns:
            (True, None) on success.
            (False, (status_code, message)) on failure.
        """
        try:
            # Fetch the post
            post = self.db.query(Post).filter(Post.id == post_id).with_for_update().first()
            if not post:
                return False, (404, "Post not found")

            # Authorization check
            if post.user_id != user_id:
                return False, (403, "Not authorized to delete this post")

            # Perform deletion
            self.db.delete(post)
            self.db.commit()
            logger.info("Community post deleted | post_id=%s | user_id=%s", post_id, user_id)
            return True, None
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "Error deleting community post | post_id=%s | user_id=%s | error=%s",
                post_id,
                user_id,
                exc,
            )
            return False, (500, "Failed to delete post")

    def list_posts(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        cursor: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> Tuple[Optional[dict], Optional[Tuple[int, str]]]:
        """Return paginated posts ordered by newest first with likes and comments counts."""
        try:
            if page < 1:
                page = 1
            if per_page < 1:
                per_page = 20

            # Create subqueries for counts
            likes_subquery = (
                select(
                    PostLike.post_id,
                    func.count(PostLike.id).label("likes_count")
                )
                .group_by(PostLike.post_id)
                .subquery()
            )
            
            comments_subquery = (
                select(
                    PostComment.post_id,
                    func.count(PostComment.id).label("comments_count")
                )
                .group_by(PostComment.post_id)
                .subquery()
            )

            # Create subquery for is_liked (if user_id provided)
            if user_id:
                is_liked_subquery = (
                    select(
                        PostLike.post_id,
                        func.cast(1, Integer).label("user_liked")
                    )
                    .where(PostLike.user_id == user_id)
                    .group_by(PostLike.post_id)
                    .subquery()
                )

                # Base query with joins for counts and is_liked
                query = (
                    self.db.query(
                        Post,
                        func.coalesce(likes_subquery.c.likes_count, 0).label("likes_count"),
                        func.coalesce(comments_subquery.c.comments_count, 0).label("comments_count"),
                        func.coalesce(is_liked_subquery.c.user_liked, 0).label("is_liked")
                    )
                    .outerjoin(likes_subquery, Post.id == likes_subquery.c.post_id)
                    .outerjoin(comments_subquery, Post.id == comments_subquery.c.post_id)
                    .outerjoin(is_liked_subquery, Post.id == is_liked_subquery.c.post_id)
                    .options(
                        joinedload(Post.user),
                        subqueryload(Post.photos),
                        subqueryload(Post.comments).joinedload(PostComment.user)
                    )
                    .order_by(Post.created_at.desc(), Post.id.desc())
                )
            else:
                # Base query with joins for counts only
                query = (
                    self.db.query(
                        Post,
                        func.coalesce(likes_subquery.c.likes_count, 0).label("likes_count"),
                        func.coalesce(comments_subquery.c.comments_count, 0).label("comments_count"),
                        func.cast(0, Integer).label("is_liked")
                    )
                    .outerjoin(likes_subquery, Post.id == likes_subquery.c.post_id)
                    .outerjoin(comments_subquery, Post.id == comments_subquery.c.post_id)
                    .options(
                        joinedload(Post.user),
                        subqueryload(Post.photos),
                        subqueryload(Post.comments).joinedload(PostComment.user)
                    )
                    .order_by(Post.created_at.desc(), Post.id.desc())
                )

            # Keyset pagination
            next_cursor: Optional[str] = None
            items: List[Post] = []

            if cursor:
                try:
                    created_at_str, id_str = cursor.split("|", 1)
                    if created_at_str.endswith("Z"):
                        created_at_str = created_at_str[:-1] + "+00:00"
                    cursor_dt = datetime.fromisoformat(created_at_str)
                    cursor_id = UUID(id_str)
                except Exception as exc:
                    logger.exception("Invalid cursor provided: %s", cursor)
                    return None, (400, "Invalid cursor format; expected '<ISO datetime>|<uuid>'")

                results = (
                    query.filter(
                        or_(
                            Post.created_at < cursor_dt,
                            and_(Post.created_at == cursor_dt, Post.id < cursor_id),
                        )
                    )
                    .limit(per_page)
                    .all()
                )
                total = None
            else:
                results = query.offset((page - 1) * per_page).limit(per_page).all()
                try:
                    total = self.db.query(Post).count()
                except Exception:
                    logger.exception("Failed to compute total count for posts")
                    total = None

            # Extract posts and attach counts and is_liked as attributes
            items = []
            for result in results:
                post = result[0]
                post.likes_count = result[1]
                post.comments_count = result[2]
                post.is_liked = bool(result[3]) if result[3] is not None else False
                
                items.append(post)

            # Compute next cursor
            if items:
                last = items[-1]
                try:
                    next_cursor = f"{last.created_at.isoformat()}|{last.id}"
                except Exception:
                    logger.exception("Failed to compute next_cursor for post id=%s", getattr(last, "id", None))
                    next_cursor = None

            result = {"items": items, "total": total, "next_cursor": next_cursor}
            return result, None

        except Exception as exc:
            logger.error("Error listing posts | page=%s | per_page=%s | error=%s", page, per_page, exc)
            return None, (500, "Failed to fetch posts")

    async def create_post_with_files(
        self,
        *,
        user_id: UUID,
        title: str,
        content: str,
        files: List[UploadFile],
        request: Request
    ) -> Tuple[Optional[Post], Optional[Tuple[int, str]]]:
        """Create post and upload files in one operation"""
        from api.v1.services.image import ImageService
        from api.utils.responses import JSONResponse
        
        try:
            # Create the post
            post = Post(
                user_id=user_id, 
                title=title, 
                content=content
            )
            post.insert(self.db, commit=False)
            
            # Upload and attach photos
            if files:
                for file in files:
                    # Use your existing ImageService to upload
                    response = await ImageService.save_and_compress_image(
                        request=request,
                        file=file,
                        db=self.db
                    )
                    
                    # Check if upload was successful
                    if isinstance(response, JSONResponse):
                        if response.status_code != 201:
                            self.db.rollback()
                            # Extract error message from response
                            response_data = response.body
                            try:
                                if hasattr(response_data, 'decode'):
                                    response_data = json.loads(response_data.decode('utf-8'))
                                else:
                                    response_data = json.loads(response_data)
                                error_msg = response_data.get('message', 'Failed to upload image')
                            except Exception as e:
                                error_msg = f"Failed to parse error response: {str(e)}"
                            return None, (response.status_code, error_msg)
                        
                        # Extract photo data from successful response
                        response_data = response.body
                        try:
                            if hasattr(response_data, 'decode'):
                                response_data = json.loads(response_data.decode('utf-8'))
                            else:
                                response_data = json.loads(response_data)
                            
                            # Check if the response has the expected structure
                            if "data" in response_data and "image_url" in response_data["data"]:
                                post_photo = PostPhoto(
                                    post_id=post.id,
                                    url=response_data["data"]["image_url"]
                                )
                                post_photo.add(self.db)
                            else:
                                logger.error(
                                    "Unexpected response structure from ImageService | response=%s",
                                    response_data
                                )
                                self.db.rollback()
                                return None, (500, "Invalid response from image service")
                        except Exception as e:
                            logger.error(
                                "Failed to parse ImageService response | error=%s",
                                str(e)
                            )
                            self.db.rollback()
                            return None, (500, "Failed to process image upload response")
                    else:
                        # Handle if response is not JSONResponse
                        self.db.rollback()
                        return None, (500, "Unexpected response from image service")
            
            # Commit all changes
            self.db.commit()
            
            try:
                self.db.refresh(post)
            except Exception as exc_refresh:
                logger.warning(
                    "Failed to refresh post after creation | post_id=%s | user_id=%s | error=%s",
                    getattr(post, "id", None),
                    user_id,
                    exc_refresh,
                )

            logger.info(
                "Community post created with files | post_id=%s | user_id=%s | file_count=%s", 
                post.id, 
                user_id,
                len(files)
            )
            return post, None

        except Exception as exc:  
            logger.error(
                "Error creating community post with files | user_id=%s | title=%s | error=%s",
                user_id,
                title,
                exc,
            )
            self.db.rollback()
            return None, (500, "Failed to create post with files")

    def _validate_photo_ids(self, photo_ids: List[UUID]) -> Tuple[bool, Optional[str]]:
        """Validate that photo IDs exist in database"""
        if not photo_ids:
            return True, None
            
        photos = Photos.fetch_all(self.db)
        existing_ids = {str(photo.id) for photo in photos}
        
        missing_ids = []
        for photo_id in photo_ids:
            if str(photo_id) not in existing_ids:
                missing_ids.append(str(photo_id))
        
        if missing_ids:
            return False, f"Photos not found: {', '.join(missing_ids)}"
        
        return True, None
    
    def get_post_with_photos(self, post_id: UUID) -> Optional[Post]:
        """
        Get a post with its photos loaded
        """
        return Post.fetch_unique(self.db, id=post_id)

    def add_photo_to_post(self, post_id: UUID, photo_id: UUID) -> Tuple[Optional[PostPhoto], Optional[Tuple[int, str]]]:
        """
        Add an existing photo to a post
        """
        try:
            # Check if post exists
            post = Post.fetch_one(self.db, id=post_id)
            if not post:
                return None, (404, "Post not found")
            
            # Check if photo exists
            photo = Photos.fetch_one(self.db, id=photo_id)
            if not photo:
                return None, (404, "Photo not found")
            
            # Check if photo is already attached to this post
            existing_photo = PostPhoto.fetch_one(self.db, post_id=post_id, url=photo.image_url)
            if existing_photo:
                return None, (400, "Photo already attached to this post")
            
            # Create PostPhoto record
            post_photo = PostPhoto(
                post_id=post_id,
                url=photo.image_url
            )
            post_photo.insert(self.db)
            
            logger.info(
                "Photo added to post | post_id=%s | photo_id=%s | post_photo_id=%s",
                post_id,
                photo_id,
                post_photo.id
            )
            return post_photo, None
            
        except Exception as exc:
            logger.error(
                "Error adding photo to post | post_id=%s | photo_id=%s | error=%s",
                post_id,
                photo_id,
                exc
            )
            return None, (500, "Failed to add photo to post")

    def remove_photo_from_post(self, post_photo_id: UUID) -> Tuple[bool, Optional[Tuple[int, str]]]:
        """
        Remove a photo from a post
        """
        try:
            post_photo = PostPhoto.fetch_one(self.db, id=post_photo_id)
            if not post_photo:
                return False, (404, "Post photo not found")
            
            post_photo.delete(self.db)
            
            logger.info(
                "Photo removed from post | post_photo_id=%s | post_id=%s",
                post_photo_id,
                post_photo.post_id
            )
            return True, None
            
        except Exception as exc:
            logger.error(
                "Error removing photo from post | post_photo_id=%s | error=%s",
                post_photo_id,
                exc
            )
            return False, (500, "Failed to remove photo from post")

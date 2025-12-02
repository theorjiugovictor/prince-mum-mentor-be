from api.v1.models.community.post_comments import PostComment
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
import uuid

from api.v1.models.community.posts import Post
from api.v1.models.community.post_likes import PostLike
from api.utils.logger import logger

class CommunityService:
    @staticmethod
    def get_post_by_id(session: Session, post_id: uuid.UUID, user_id: uuid.UUID) -> Post:
        """
        Fetches a post by ID, eager loads photos, comments with users, and increments view count.
        """
        logger.info(f"Fetching post details for {post_id}")

        post = session.query(Post).options(
            joinedload(Post.photos),
            joinedload(Post.likes),  
            joinedload(Post.comments).joinedload(PostComment.user),
            joinedload(Post.user)
        ).filter(Post.id == post_id).first()

        if not post:
            logger.warning(f"Post {post_id} not found")
            raise HTTPException(status_code=404, detail="Post not found")

        # Check if current user liked this post
        is_liked = session.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id
        ).first() is not None
        post.is_liked = is_liked

        # Set counts
        post.likes_count = len(post.likes)
        post.comments_count = len(post.comments)

        post.views += 1
        try:
            session.commit()
            session.refresh(post)
        except Exception as e:
            logger.error(f"Failed to update view count for post {post_id}: {e}")
            session.rollback()

        return post
    
    @staticmethod
    def toggle_post_like(
        session: Session, 
        post_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> tuple[bool, int]:
        """
        Toggle like on a post. Returns (is_liked, total_likes_count)
        - If user already liked: remove like (unlike)
        - If user hasn't liked: add like
        
        Args:
            session: Database session
            post_id: ID of the post to like/unlike
            user_id: ID of the user performing the action
            
        Returns:
            Tuple of (is_liked: bool, total_likes_count: int)
        
        Raises:
            HTTPException: If post not found
        """
        logger.info(f"Toggling like for post {post_id} by user {user_id}")
        
        # Check if post exists
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post:
            logger.warning(f"Post {post_id} not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        
        # Check if user already liked this post
        existing_like = session.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id
        ).first()
        
        try:
            if existing_like:
                # Unlike: Delete the existing like
                session.delete(existing_like)
                is_liked = False
                logger.info(f"User {user_id} unliked post {post_id}")
            else:
                # Like: Create a new like
                new_like = PostLike(
                    post_id=post_id,
                    user_id=user_id
                )
                session.add(new_like)
                is_liked = True
                logger.info(f"User {user_id} liked post {post_id}")

            # Make pending changes available for the count query
            session.flush()

            # Get updated likes count
            likes_count = session.query(PostLike).filter(PostLike.post_id == post_id).count()

            # Commit the whole transaction
            session.commit()

            return (is_liked, likes_count)
            
        except Exception as e:
            logger.error(f"Failed to toggle like for post {post_id}: {e}")
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process like action"
            )
    
    @staticmethod
    def add_comment_to_post(session: Session, post_id: uuid.UUID, user_id: uuid.UUID, comment: str) -> PostComment:
        """
        Add a comment to a post (no nested comments).
        """
        from datetime import datetime, timezone
        
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        now = datetime.now(timezone.utc)
        new_comment = PostComment(
                post_id=post_id,
                user_id=user_id,
                comment=comment,
                created_at=now,
                updated_at=now
        )
        session.add(new_comment)
        session.commit()
        session.refresh(new_comment)
        return new_comment
        
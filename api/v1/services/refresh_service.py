import hmac
import hashlib
import os
import jwt
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, Dict, Any

from api.v1.models.user.user import UserAuthSession, User, UserActivityLog
from api.utils.logger import logger
from api.utils.login import create_access_token, create_refresh_token


def _hash_token(token: str) -> str:
    key = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


def refresh_access_token_service(
    db, incoming_token: str, device_header: Optional[str], client_host: Optional[str], user_agent: Optional[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Service to refresh tokens. Returns (data, error)."""
    now = datetime.now(timezone.utc)
    try:
        # Verify token signature & expiry
        JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
        ALGORITHM = os.getenv("ALGORITHM", "HS256")
        
        try:
            payload = jwt.decode(incoming_token, JWT_SECRET, algorithms=[ALGORITHM])
        except Exception as e:
            return None, {"status_code": 401, "message": "Invalid or expired refresh token."}

        # Extract user_id from nested structure
        user_id = payload.get("user", {}).get("user_id")
        if not user_id:
            return None, {"status_code": 401, "message": "Invalid token payload"}

        token_hash = _hash_token(incoming_token)

        # Find session by hashed token
        session = None
        if hasattr(db, "query"):
            try:
                session = db.query(UserAuthSession).filter(
                    UserAuthSession.refresh_token == token_hash
                ).first()
            except Exception:
                session = None

        if session is None:
            session = UserAuthSession.fetch_unique(db, refresh_token=token_hash)

        if not session:
            return None, {"status_code": 401, "message": "Invalid refresh token provided."}

        if session.is_revoked:
            return None, {"status_code": 401, "message": "Refresh token revoked."}

        if session.expires_at and session.expires_at < now:
            return None, {"status_code": 401, "message": "Refresh token expired."}

        if session.device_id and device_header and session.device_id != device_header:
            return None, {"status_code": 403, "message": "Device mismatch for refresh token."}

        # Load user
        if hasattr(db, "query"):
            try:
                user = db.query(User).filter(User.id == session.user_id).first()
            except Exception:
                user = None
        else:
            user = User.fetch_unique(db, id=session.user_id)
            
        if not user:
            return None, {"status_code": 401, "message": "User not found for token."}

        # Create new tokens using utils/login
        access_token, _ = create_access_token(user.id, user.role)
        new_refresh, _ = create_refresh_token(user.id, user.role)

        # Rotate stored token (hash it)
        session.refresh_token = _hash_token(new_refresh)
        session.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session.updated_at = now

        activity = UserActivityLog(
            user_id=session.user_id,
            activity_type="refresh_token",
            ip_address=client_host,
            user_agent=user_agent,
            activity_metadata={"rotated": True},
        )

        db.add(activity)
        db.add(session)
        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": new_refresh,
            "user_id": str(user.id),
        }, None

    except Exception as e:
        try:
            logger.error(f"Error in refresh_access_token_service: {str(e)}")    
            db.rollback()
        except Exception:
            pass
        return None, {"status_code": 500, "message": "An unexpected error occurred during token refresh."}
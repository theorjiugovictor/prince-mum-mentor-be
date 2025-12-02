"""Authentication and Authorization related routes"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from api.db.database import get_db

from api.v1.models.user.user import User, UserAuthSession, UserActivityLog

from api.v1.schemas.delete_account import AccountDeletionRequest
from api.v1.schemas.login import LoginRequest
from api.v1.schemas.logout import LogoutResponse
from api.v1.schemas.forgot_password import ForgotPassword
from api.v1.schemas.reset_password import ResetPassword
from api.v1.schemas.change_password import ChangePasswordRequest
from api.v1.schemas.user import (
    UserRegistrationRequest,
    UserRegistrationResponse,
    EmailVerificationRequest,
    ResendVerificationRequest,
)
from api.v1.schemas.verify_otp import VerifyOTPRequest
from api.v1.schemas.google_auth_schema import (
    GoogleAuthRequest,
    GoogleAuthResponse,
    UserResponse,
    RefreshTokenRequest,
    RevokeRequest,
)

from api.v1.services.delete_account import AccountService
from api.v1.services.user_service import UserService
from api.v1.services.email_verification import EmailVerificationService
from api.v1.services.email_services import send_email
from api.v1.services.forgot_password import forgot_password_service
from api.v1.services.reset_password import reset_password_service
from api.v1.services.change_password import change_user_password
from api.v1.services.verify_otp import VerifyOTPService
from api.v1.services.google_auth import (
    google_auth_service,
    run_verify,
    GoogleVerificationResponse,
)
from api.v1.services.refresh_service import refresh_access_token_service
from api.v1.services.refresh_service import _hash_token
from api.v1.services.logout import Logout

from api.utils.security import verify_password
from api.utils.responses import (
    auth_response,
    success_response,
    fail_response,
    JSONResponse,
)
from api.utils.login import create_access_token, create_refresh_token, get_device_info
from api.utils.deps import get_current_user, security
from api.utils.logger import logger

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
google_auth_router = APIRouter(prefix="/google", tags=["Google Authentication"])


@auth_router.delete(
    "/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete user account",
    description="Permanently delete user account and all associated data. Requires password confirmation."
)
async def delete_account(
    request: AccountDeletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete user account permanently.
    
    - **password**: Current password for confirmation
    - **confirmation_phrase**: Must be exactly "DELETE MY ACCOUNT"
    - **reason**: Optional reason for deletion (max 100 characters)
    
    This action cannot be undone. All user data will be permanently removed.
    """
    logger.info("Account deletion request for user: %s", current_user.email)
    
    # Check if account is already deleted
    if current_user.is_deleted:
        logger.warning("Attempt to delete already deleted account: %s", current_user.id)
        return fail_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Account already deleted"
        )

    # Delete account
    success, error = AccountService.delete_user_account(
        db, str(current_user.id), request.password, request.reason
    )
    
    if not success:
        logger.warning(
            "Account deletion failed for user %s: %s",
            current_user.email,
            error
        )
        return fail_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error
        )

    # Send confirmation email (optional)
    try:
        if current_user.email and not current_user.email.startswith("deleted_"):
            subject = "Account Deletion Confirmation"
            body = f"""Hi {current_user.full_name},

Your account and all associated data have been permanently deleted from our systems.

If this was a mistake or you change your mind, please contact our support team immediately.

We're sorry to see you go!

Best regards,
The Nora Team"""
            
            await send_email(current_user.email, subject, body)
            logger.info("Deletion confirmation email sent to: %s", current_user.email)
    except Exception as email_error:
        logger.error(
            "Failed to send deletion confirmation email to %s: %s",
            current_user.email,
            str(email_error),
            exc_info=True
        )
        # Don't fail the request if email fails

    logger.info(
        "Account successfully deleted for user: %s%s",
        current_user.email,
        f" (Reason: {request.reason})" if request.reason else ""
    )
    
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Account and all associated data have been permanently deleted",
        data={
            "deletion_time": datetime.now(timezone.utc).isoformat()
        }
    )
    
@auth_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="User Login",
    response_description="JWT tokens and user data",
    responses={
        200: {"description": "Successful login with tokens"},
        401: {"description": "Invalid credentials"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
def login_route(
    request: LoginRequest, db: Session = Depends(get_db), client: Request = None
):
    """
    Authenticate user and return JWT tokens for API access.

    - Verifies email/password against stored credentials
    - Returns access_token (30min) and refresh_token (7days)
    - Tracks login activity and device information

    Example request:
    ```json
    {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
    ```
    """

    try:
        ip_address = client.client.host if client.client else None
        user_agent = client.headers.get("User-Agent")
        device_name = get_device_info(user_agent).get("device")

        logger.info("Login attempt for email: %s", request.email)

        user = User.fetch_unique(db, email=request.email.lower(), is_active=True)
        if not user:
            logger.warning("User not found or not active: %s", request.email)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Active user not found"
            )

        password_match = verify_password(request.password, str(user.password_hash))
        logger.info("Password verification result: %s", password_match)

        if not password_match:
            logger.warning("Password mismatch for user: %s", user.email)
            log = UserActivityLog(
                user_id=user.id,
                activity_type="login",
                ip_address=ip_address,
                user_agent=user_agent,
                activity_metadata={
                    "status": "unsuccessful",
                    "details": "invalid password",
                },
            )
            log.insert(db)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        logger.info("Login successful for user: %s", user.email)

        # Update user using BaseModel method
        user.last_login_at = datetime.now(timezone.utc)
        user.update(db)

        access_token, _ = create_access_token(user.id, user.role)
        refresh_token, refresh_expires = create_refresh_token(user.id, user.role)

        session = UserAuthSession(
            user_id=user.id,
            refresh_token=_hash_token(refresh_token),
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
            expires_at=refresh_expires,
        )

        session.insert(db)

        log = UserActivityLog(
            user_id=user.id,
            activity_type="login",
            ip_address=ip_address,
            user_agent=user_agent,
            activity_metadata={"status": "success"},
        )
        log.insert(db)

        return auth_response(
            status_code=200,
            message="Login successful",
            access_token=access_token,
            refresh_token=refresh_token,
            data={
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                }
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("exception occurred in login route: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e


@auth_router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    responses={
        200: {"description": "Successfully logged out"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"},
    },
)
def logout_route(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log out user and blacklist current access token.

    - Blacklists the current JWT access token
    - Logs the logout activity
    - Token becomes immediately invalid
    """
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        device_name = (
            get_device_info(user_agent).get("device") if user_agent else "Unknown"
        )

        token = credentials.credentials

        logger.info("Logout initiated for user: %s", current_user.email)

        # Blacklist the current token
        auth_service = Logout(db)
        success = auth_service.logout_user(token, current_user.id)

        if not success:
            logger.warning("Failed to blacklist token for user: %s", current_user.email)

        # Log the logout activity
        log = UserActivityLog(
            user_id=current_user.id,
            activity_type="logout",
            ip_address=ip_address,
            user_agent=user_agent,
            activity_metadata={
                "status": "success",
                "device": device_name,
                "token_blacklisted": success,
            },
        )
        log.insert(db)

        return success_response(
            status_code=200,
            message="Logout successful. Token has been revoked.",
            data={"success": True},
        )

    except Exception as e:
        logger.error(
            "Error during logout for user %s: %s",
            current_user.email,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout",
        ) from e


@auth_router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    summary="Verify user email",
    description="""
        Verify a user's email address using a verification token.

        This endpoint confirms a user's email by validating the verification token sent
        to their registered email address.

        ### How It Works
        - The user receives an email containing a verification link with a *token*.
        - The user clicks the link, which calls this endpoint.
        - If the token is valid and not expired, the user's email is marked as verified.""",
)
def verify_email(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify user email"""
    logger.info("Email verification attempt with token")

    user, error = EmailVerificationService.verify_email_token(db, request.token)

    if error:
        logger.warning("Email verification failed: %s", error)
        return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)

    if not user:
        logger.error("Email verification returned None without error")
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to verify email",
        )

    logger.info("Email verified successfully for user: %s", user.email)
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Email verified successfully",
        data={"email_verified": True},
    )


@auth_router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    summary="Resend verification email",
    description="""Resend email verification link to user
        Resend Email Verification Link

        This endpoint allows a user to request a new email verification link if they
        did not receive the original one or it has expired.

        ### When to Use This
        - The user registered but never received the verification email.
        - The user’s previous verification token has expired.
        - The user wants a fresh verification link.""",
)
async def resend_verification(
    request: ResendVerificationRequest, db: Session = Depends(get_db)
):
    """Resend verification email"""
    logger.info("Resend verification request for email: %s", request.email)

    user = User.fetch_unique(db, email=request.email.lower())

    if not user:
        # Return generic message for security
        return success_response(
            status_code=status.HTTP_200_OK,
            message="If the email exists, a verification link has been sent",
        )

    if user.email_verified:
        logger.info("User email already verified: %s", request.email)
        return fail_response(
            status_code=status.HTTP_409_CONFLICT, message="Email is already verified"
        )

    recent_count = EmailVerificationService.get_recent_verification_count(
        db, str(user.id), minutes=60
    )

    if recent_count >= 3:
        logger.warning("Rate limit exceeded for user: %s", request.email)
        return fail_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message="Too many verification requests. Please try again later",
        )

    success, invalidate_error = EmailVerificationService.invalidate_old_tokens(
        db, str(user.id)
    )
    if not success:
        db.rollback()
        logger.error(
            "Failed to invalidate old tokens for: %s. Error: %s",
            request.email,
            invalidate_error,
        )
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to invalidate old verification tokens",
        )

    verification_token, error = EmailVerificationService.create_verification_record(
        db, str(user.id)
    )

    if error or not verification_token:
        db.rollback()
        logger.error("Failed to create verification token for: %s", request.email)
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to generate verification token",
        )

    # Commit all changes atomically
    db.commit()
    db.refresh(verification_token)

    if not user.email:
        logger.error("User has no email address: %s", str(user.id))
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="User email not found",
        )

    try:
        subject = "Verify Your Email Address"
        body = f"""Hi {user.full_name},

We're so glad to have you here. You're one step closer to experiencing a calmer, more supported motherhood journey with Nora.

Whether you're navigating pregnancy, caring for a newborn, or guiding a growing child — Nora is here with trusted answers, gentle guidance, and support whenever you need it.

Please use the verification code below to confirm your email and complete your setup:

{verification_token.token}

This verification code will expire in {EmailVerificationService.TOKEN_EXPIRY_MINUTES} minutes.

Thanks,
The Nora Team"""

        # Send email and check if it was successful
        await send_email(user.email, subject, body)

        logger.info("Verification email sent successfully to: %s", request.email)

    except Exception as email_error:
        logger.error(
            "Failed to send verification email to %s: %s",
            request.email,
            str(email_error),
            exc_info=True,
        )
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send verification email. Please try again later.",
        )

    return success_response(
        status_code=status.HTTP_200_OK, message="Verification email sent successfully"
    )


@auth_router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    response_description="New access and refresh tokens",
    responses={
        200: {"description": "Access token refreshed successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Device mismatch for refresh token"},
        500: {"description": "Internal server error"},
    },
)
def refresh_access_token(
    payload: RefreshTokenRequest,
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    Refresh an access token using a valid refresh token.
    

    Security measures implemented:
    - Validates the refresh token exists in the DB and is not revoked.
    - Ensures the refresh session has not expired.
    - Optionally enforces device binding via `X-Device-Id` header when available.
    - Rotates the refresh token on success and updates expiry.
    - Logs the refresh action in `user_activity_logs`.
    """

    if not payload or not payload.refresh_token:
        return fail_response(
            status.HTTP_401_UNAUTHORIZED, 
            "Missing refresh token in request body"
        )

    incoming_token = payload.refresh_token.strip()
    device_header = request.headers.get("X-Device-Id")
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    logger.info("Email/password refresh token request received")

    data, error = refresh_access_token_service(
        db, incoming_token, device_header, client_host, user_agent
    )

    if error:
        logger.warning(
            "Refresh token error: %(message)s", {"message": error.get("message")}
        )
        return fail_response(
            error.get("status_code", status.HTTP_401_UNAUTHORIZED), 
            error.get("message")
        )

    logger.info("Access token refreshed successfully for user: %s", data.get("user_id"))
    
    return auth_response(
        status.HTTP_200_OK,
        "Access token refreshed successfully.",
        data.get("access_token"),
        data.get("refresh_token"),
        data={"user_id": data.get("user_id")},
    )


@google_auth_router.post(
    "/login", status_code=status.HTTP_200_OK, response_model=GoogleAuthResponse
)
async def google_login(
    payload: GoogleAuthRequest, request: Request, db: Session = Depends(get_db)
):
    """
    Accepts a Google `id_token` from the client (React Native / Expo).
    Verifies the token with Google, creates/updates a local user,
    and returns a local access token.
    """
    logger.info("Google login attempt")
    # verify id_token with Google
    try:
        google_data: GoogleVerificationResponse | JSONResponse = await run_verify(
            payload.id_token
        )
        if not isinstance(google_data, dict):
            logger.warning("Google token verification failed")
            return google_data

        google_data = GoogleVerificationResponse(**google_data)
        user = google_auth_service.get_or_create_user(db, google_data)
        if not isinstance(user, User):
            return user
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        session = google_auth_service.create_session(
            db,
            user=user,
            device_id=payload.device_id,
            device_name=payload.device_name,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # issue local access token
        access_token = google_auth_service.issue_local_access_token(
            user, sid=str(session.id)
        )
        refresh_token = google_auth_service.issue_local_refresh_token(
            user, sid=str(session.id)
        )
    except ValueError as exc:
        logger.error("Failed to get or create user: %s", str(exc))
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create user",
        )
    except Exception as exc:
        logger.error("Failed to create local access token: %s", str(exc))
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create access token",
        )

    logger.info("Google login successful for user_id=%s ip=%s", user.id, client_ip)

    # return access token (no refresh_token stored)
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Google login successful",
        data=GoogleAuthResponse(
            access_token=access_token, refresh_token=refresh_token
        ).model_dump(),
    )



@auth_router.get("/user", status_code=status.HTTP_200_OK)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):  # wire to your deps.get_current_user
    """
    Return basic information about the currently authenticated user.
    Make sure this route uses your existing deps.get_current_user
    dependency in production.
    """
    if not current_user:
        return fail_response(
            status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized"
        )
    user_resp = UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        google_id=current_user.google_id,
        role=getattr(current_user, "role", None),
    )
    return success_response(
        status_code=status.HTTP_200_OK,
        message="User info retrieved",
        data=user_resp.model_dump(),
    )


@auth_router.post("/revoke", status_code=status.HTTP_200_OK)
async def revoke(payload: RevokeRequest, db: Session = Depends(get_db)):
    """Revoke a refresh token session
    Args:
        payload (RevokeRequest): takes in refresh token
        db (Session, optional): Defaults to Depends(get_db).
    """
    payload_data = google_auth_service.verify_token(payload.refresh_token, refresh=True)
    if isinstance(payload_data, JSONResponse):
        return payload_data
    logger.info("payload_data: %s", payload_data)
    if not payload_data:
        return fail_response(
            status_code=status.HTTP_401_UNAUTHORIZED, message="Invalid refresh token"
        )

    sid = payload_data.get("sid")

    success = google_auth_service.revoke_session(db, str(sid))
    if not success:
        return fail_response(
            status_code=status.HTTP_400_BAD_REQUEST, message="Failed to revoke session"
        )
    return success_response(
        status_code=status.HTTP_200_OK, message="Session revoked successfully"
    )


# @auth_router.post("/revoke-access", status_code=status.HTTP_200_OK)
# async def revoke(payload: RevokeRequest, db: Session = Depends(get_db)):
#     """Revoke a refresh token session
#     Args:
#         payload (RevokeRequest): takes in refresh token
#         db (Session, optional): Defaults to Depends(get_db).
#     """
#     payload_data = google_auth_service.verify_token(payload.refresh_token, refresh=False)
#     logger.info(f"payload_data: {payload_data}")
#     if not payload_data:
#         return fail_response(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             message="Invalid refresh token"
#         )

#     sid = payload_data.get("sid")

#     success = google_auth_service.revoke_session(db, str(sid))
#     if not success:
#         return fail_response(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             message="Failed to revoke session"
#         )
#     return success_response(
#         status_code=status.HTTP_200_OK,
#         message="Session revoked successfully"
#     )


@auth_router.post(
    "/verify-otp",
    status_code=status.HTTP_200_OK,
    summary="Verify OTP",
    description="""
    (Step 2 of 3) of Resetting User Password
    Verify the OTP code sent to the user's email.

    This step confirms the user's identity and allows them to proceed to the final
    password reset stage. for the final stage use reset-password endpoint
""",
)
async def verify_otp(
    request_data: VerifyOTPRequest,
    db: Session = Depends(get_db),
    client: Request = None,
):
    """
    Verify OTP endpoint

    Verifies the OTP code and returns JWT tokens for authentication.
    After successful verification, the user is automatically logged in.
    """
    user, error = VerifyOTPService.verify_otp(db, request_data)

    if error:
        return fail_response(status_code=status.HTTP_400_BAD_REQUEST, message=error)

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, user.role)

    # Get device information
    ip_address = client.client.host if client and client.client else None
    user_agent = client.headers.get("User-Agent") if client else None
    device_name = get_device_info(user_agent).get("device") if user_agent else None

    # Create auth session using BaseModel pattern
    session = UserAuthSession(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
        device_name=device_name,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.insert(db)  # Using BaseModel insert method

    logger.info("OTP verification successful for user: %s", user.email)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="OTP verified successfully",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user.id,
        },
    )


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    response_description="User registration data",
    responses={
        201: {"description": "User successfully registered"},
        422: {"description": "Invalid input or validation error"},
        409: {"description": "Email already registered"},
        500: {"description": "Internal server error"},
    },
)
async def register_user(
    user_data: UserRegistrationRequest, db: Session = Depends(get_db)
):
    """
    Register a new user account.

    - **full_name**: User's full name (2-100 characters)
    - **email**: Valid email address (must be unique)
    - **phone**: Optional phone number (max 20 characters)
    - **password**: Strong password (min 8 chars, uppercase, lowercase,
      digit, special char)
    - **confirm_password**: Must match password

    Returns user data.
    """
    logger.info("Registration attempt for email: %s", user_data.email)

    user, context, verification_token = await UserService.create_user(db, user_data)

    if context:
        logger.warning(
            "Registration failed for %s: %s",
            user_data.email,
            context,
        )
        # Return 409 Conflict for already registered users
        if context.get("is_registered") is True:
            return fail_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Email already registered. Please login or reset your password.",
                context=context,
            )
        # Return 400 Bad Request for other errors
        return fail_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=context.get(
                "message", "An unknown error occurred during registration."
            ),
            context=context,
        )

    if not user:
        logger.error(
            "User creation returned None without error for %s",
            user_data.email,
        )
        return fail_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create user",
        )

    # Send welcome email
    if verification_token and user.email:
        subject = "Welcome to Nora!"
        body = f"""Hi {user.full_name},

We're so glad to have you here. You're one step closer to experiencing a calmer,
more supported motherhood journey with Nora.

Whether you're navigating pregnancy, caring for a newborn, or guiding a growing
child — Nora is here with trusted answers, gentle guidance, and support
whenever you need it.

Your account is now active and ready to use. You can start chatting with Nora right away!

Thanks,
The Nora Team"""

        await send_email(user.email, subject, body)

    # Prepare response data
    user_response = UserRegistrationResponse(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )

    logger.info("Registration successful for user: %s", user.email)
    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Welcome to Nora! Your account has been created successfully.",
        data=user_response.model_dump(),
    )


@auth_router.get("/validate-token")
def validate_token(current_user: User = Depends(get_current_user)):
    """
    Validate JWT access token.

    This endpoint validates the JWT token from the Authorization header
    and returns whether it's valid or not along with basic user information.

    How it works:
    - Client sends request with Bearer token in Authorization header
    - Server validates the token using get_current_user middleware
    - If valid, returns success with user info
    - If invalid/expired, returns 401 Forbidden

    Returns:
        200: Token is valid with user information
        401: Token is invalid or expired

    Example Response:
    {
        "status": "success",
        "status_code": 200,
        "message": "Token is valid",
        "data": {
            "valid": true
        }
    }
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid"
        )
    return success_response(
        status_code=status.HTTP_200_OK, message="Token is valid", data={"valid": True}
    )


@auth_router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(request: ForgotPassword, db: Session = Depends(get_db)):
    """
    Forgot Password (Step 1 of 3)

    First step in the password reset flow for logged-out users.

    ### Step-by-Step Reset Process
    1. **Forgot Password (this endpoint)**
       - User submits their email
       - A password reset OTP/code is generated and sent to the user's email

    2. **Verify OTP**
       - User enters the OTP received in their email to confirm ownership

    3. **Reset Password**
       - After OTP verification, user submits a new password to complete the reset

    ### What This Endpoint Does
    - Checks if the email belongs to a registered user
    - Generates a one-time OTP/reset code
    - Sends the OTP to the user's email address

    ### Next Step
    Use the received OTP with the `/auth/verify-otp` endpoint for Step 2.
    """
    result = await forgot_password_service(db, request.email)

    return success_response(
        status_code=status.HTTP_200_OK,
        message=result["message"],
        data={"email": result["email"]},
    )


@auth_router.patch("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: ResetPassword, db: Session = Depends(get_db)):
    """
    Reset User Password (Step 3 of 3)

    Final step of the password reset flow. Updates the user's password
    after OTP verification.

    ### Request Body
    - `new_password`: The new password
    - `confirm_password`: Must match new_password

    ### Returns
    A success message confirming the password has been reset.
    """
    reset_password_service(db, request)

    return success_response(
        status_code=status.HTTP_200_OK, message="Password reset successfully"
    )


@auth_router.patch("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Change Password (Logged-in Users Only)

    Allows an authenticated user to change their password while logged in.

    ### How to Test in Swagger
    1. Login first using the `/auth/login` endpoint
    2. Copy the `access_token` from the login response
    3. Click the **Authorize** button at the top of the Swagger page
    4. Paste ONLY the token (Swagger adds "Bearer" automatically)
    5. Open `/auth/change-password` and click **Try it out**

    ### Request Body Example
    ```json
    {
        "old_password": "OldPass123!",
        "new_password": "NewPass456!",
        "confirm_password": "NewPass456!"
    }
    ```
    """
    # Validate password confirmation
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match",
        )

    # Attempt password change
    success, message = change_user_password(
        current_user, request.old_password, request.new_password, db
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return success_response(status_code=status.HTTP_200_OK, message=message)
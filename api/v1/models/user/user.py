import uuid
from datetime import datetime, date, time, timezone
from sqlalchemy import Boolean, String, Text, DateTime, Date, Time, ForeignKey, Integer, JSON, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from api.db.base_model import BaseModel, Base
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from api.v1.models.community.posts import Post

class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    password_hash: Mapped[str | None] = mapped_column(Text)
    google_id: Mapped[str | None] = mapped_column(String(200), unique=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)

    role: Mapped[str] = mapped_column(String(20), default="user")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


    # Relationships    
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    sessions = relationship("UserAuthSession", back_populates="user")
    otp_codes = relationship("UserOTPVerification", back_populates="user")
    activities = relationship("UserActivityLog", back_populates="user")
    verification_tokens = relationship("EmailVerificationToken", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user")



class UserProfile(BaseModel):
    __tablename__ = "user_profile"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    date_of_birth: Mapped[date | None] = mapped_column(Date)
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="Nigeria")

    occupation: Mapped[str | None] = mapped_column(String(200))
    tech_savviness: Mapped[int | None] = mapped_column(Integer)

    preferred_language: Mapped[str] = mapped_column(String(50), default="en")
    ai_tone_preference: Mapped[str] = mapped_column(String(20), default="caring")

    onboarding_stage: Mapped[str | None] = mapped_column(String(20))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    push_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    timezone: Mapped[str] = mapped_column(String(50), default="Africa/Lagos")

    avatar_url: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", back_populates="profile")


class UserSettings(BaseModel):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    dark_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_voice_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_reminder_time: Mapped[time] = mapped_column(Time, default="09:00:00")

    chat_history_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    show_milestone_reminders: Mapped[bool] = mapped_column(Boolean, default=True)

    community_visibility: Mapped[str] = mapped_column(String(20), default="public")
    data_sharing_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="settings")


class UserAuthSession(BaseModel):
    __tablename__ = "user_auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    refresh_token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(200))
    device_name: Mapped[str | None] = mapped_column(String(200))
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(100))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)

    user = relationship("User", back_populates="sessions")


class UserOTPVerification(BaseModel):
    __tablename__ = "user_otp_verification"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    otp_code: Mapped[str] = mapped_column(String(10), nullable=False)
    otp_type: Mapped[str] = mapped_column(String(30), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)

    user = relationship("User", back_populates="otp_codes")


class Waitlist(Base):
    __tablename__ = "waitlist"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    phone: Mapped[str | None] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    referral_source: Mapped[str | None] = mapped_column(String(100))

    is_invited: Mapped[bool] = mapped_column(Boolean, default=False)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class FAQ(BaseModel):
    __tablename__ = "faqs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    keywords: Mapped[dict | None] = mapped_column(JSON)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class UserActivityLog(BaseModel):
    __tablename__ = "user_activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(100))
    user_agent: Mapped[str | None] = mapped_column(Text)
    activity_metadata: Mapped[dict | None] = mapped_column(JSON)

    user = relationship("User", back_populates="activities")


class EmailVerificationToken(BaseModel):
    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)

    user = relationship("User", back_populates="verification_tokens")


class ChildProfile(BaseModel):
    __tablename__ = "child_profile"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True,default=uuid.uuid4)
    profile_setup_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profile_setup.id"),nullable=False,index=True)
    full_name: Mapped[str] = mapped_column(String(120),nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50),nullable=True)
    
    # added birth_order and profile_picture_url to match the design of the child profile fields
    birth_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_setup: Mapped["ProfileSetup"] = relationship(back_populates="children")


class ProfileSetup(BaseModel):
    __tablename__ = "profile_setup"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"),nullable=False,unique=True,index=True)
    mom_status: Mapped[str] = mapped_column(nullable=False)
    goals: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    partner: Mapped[dict | None] = mapped_column(JSON,nullable=True)
    children: Mapped[list["ChildProfile"]] = relationship(back_populates="profile_setup",cascade="all, delete-orphan")
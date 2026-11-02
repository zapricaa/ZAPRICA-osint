import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, get_json_type


class BrowserProfile(Base):
    """Dedicated persistent browser profile, isolated per authorized user and service identity."""
    __tablename__ = "browser_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_name: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    encryption_key_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    sessions: Mapped[list["BrowserSession"]] = relationship("BrowserSession", back_populates="profile", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", "profile_name", name="uq_user_workspace_profile"),
    )


class BrowserSession(Base):
    """Active or historical Playwright browser session attached to an investigation."""
    __tablename__ = "browser_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("browser_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="DISCONNECTED", nullable=False)
    # DISCONNECTED, STARTING, LOGIN_REQUIRED, AUTHENTICATING, USER_AUTHENTICATED, READY, BUSY, SESSION_EXPIRED, STOPPED, ERROR

    current_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    active_tab_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auth_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    auth_confirmed_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_metadata: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    profile: Mapped["BrowserProfile"] = relationship("BrowserProfile", back_populates="sessions")
    events: Mapped[list["BrowserSessionEvent"]] = relationship("BrowserSessionEvent", back_populates="session", cascade="all, delete-orphan")
    browser_tasks: Mapped[list["BrowserTask"]] = relationship("BrowserTask", back_populates="session", cascade="all, delete-orphan")


class BrowserSessionEvent(Base):
    """Audit log of browser navigation, human login challenge, and action events."""
    __tablename__ = "browser_session_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("browser_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    session: Mapped["BrowserSession"] = relationship("BrowserSession", back_populates="events")


class BrowserTask(Base):
    """Task assigned specifically to the dedicated Browser Head Agent."""
    __tablename__ = "browser_tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("browser_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # NAVIGATE, EXTRACT_METADATA, MANUAL_LOGIN_PROMPT, CAPTURE_SCREENSHOT, IMPORT_MANUAL_DATA
    target_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    policy_checked: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED", nullable=False)
    output_summary: Mapped[Optional[Any]] = mapped_column(get_json_type(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["BrowserSession"] = relationship("BrowserSession", back_populates="browser_tasks")

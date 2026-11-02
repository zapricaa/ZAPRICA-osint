import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, get_json_type


class WebsiteAutomationPolicy(Base):
    """Explicit automation policy per website domain pattern (AUTOMATED_ALLOWED, HUMAN_ASSISTED_ONLY, API_ONLY, BLOCKED)."""
    __tablename__ = "website_automation_policies"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    domain_pattern: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    policy_type: Mapped[str] = mapped_column(String(50), default="AUTOMATED_ALLOWED", nullable=False)
    # AUTOMATED_ALLOWED, HUMAN_ASSISTED_ONLY, API_ONLY, BLOCKED

    allow_browser_automation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_automated_queries: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_automated_extraction: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_manual_user_access: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_manual_result_import: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ToolExecutionPolicy(Base):
    """Execution constraints and approval rules for specific tools."""
    __tablename__ = "tool_execution_policies"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    tool_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    execution_mode: Mapped[str] = mapped_column(String(50), default="AUTOMATED_ALLOWED", nullable=False)
    # AUTOMATED_ALLOWED, HUMAN_ASSISTED_ONLY, API_ONLY, BLOCKED

    browser_automation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    terminal_sandboxed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_admin_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class HumanApproval(Base):
    """Pending or completed operator confirmations for sensitive tasks or human-in-the-loop workflows."""
    __tablename__ = "human_approvals"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_agent: Mapped[str] = mapped_column(String(50), nullable=False)
    approval_type: Mapped[str] = mapped_column(String(50), default="TOOL_EXECUTION", nullable=False)
    # TOOL_EXECUTION, SENSITIVE_ACTION, MANUAL_SESSION_READY, IMPORT_CONFIRMATION
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    approved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


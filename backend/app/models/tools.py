import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, get_json_type


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    vendor_or_source: Mapped[str] = mapped_column(String(255), nullable=False)
    homepage_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    license_id: Mapped[str] = mapped_column(String(100), default="MIT", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    versions: Mapped[list["ToolVersion"]] = relationship("ToolVersion", back_populates="tool", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("workspace_id", "tool_key", name="uq_workspace_tool_key"),
    )


class ToolVersion(Base):
    __tablename__ = "tool_versions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    tool_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("tools.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    execution_type: Mapped[str] = mapped_column(String(50), default="library", nullable=False)  # browser, terminal, api, library
    capabilities: Mapped[Any] = mapped_column(get_json_type(), default=list, nullable=False)
    input_schema: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    output_schema: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    manifest_json: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    playbook_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    artifact_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    artifact_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    dependency_lock_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    test_result_json: Mapped[Optional[Any]] = mapped_column(get_json_type(), nullable=True)
    permission_profile: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    network_policy: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    resource_limits: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, testing, pending_review, approved, published, rejected, disabled, revoked
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    tool: Mapped["Tool"] = relationship("Tool", back_populates="versions")
    assignments: Mapped[list["AgentToolAssignment"]] = relationship("AgentToolAssignment", back_populates="tool_version", cascade="all, delete-orphan")
    tool_runs: Mapped[list["ToolRun"]] = relationship("ToolRun", back_populates="tool_version")

    __table_args__ = (
        UniqueConstraint("tool_id", "version", name="uq_tool_version"),
        Index("ix_tool_versions_approval_execution", "approval_status", "execution_type"),
    )


class AgentToolAssignment(Base):
    __tablename__ = "agent_tool_assignments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_version_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("tool_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)  # browser_head, terminal_head, worker
    capability: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scope_constraints: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    tool_version: Mapped["ToolVersion"] = relationship("ToolVersion", back_populates="assignments")

    __table_args__ = (
        UniqueConstraint("tool_version_id", "agent_type", "capability", name="uq_tool_agent_capability"),
    )

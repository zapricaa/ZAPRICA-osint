import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, get_json_type


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    investigation_type: Mapped[str] = mapped_column(String(100), default="public_website", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, queued, planning, running, awaiting_approval, paused, completed, failed, cancelled
    priority: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)  # low, medium, high, critical
    plan_json: Mapped[Optional[Any]] = mapped_column(get_json_type(), nullable=True)
    model_policy_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=90),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    scope: Mapped[Optional["InvestigationScope"]] = relationship("InvestigationScope", back_populates="investigation", uselist=False, cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="investigation", cascade="all, delete-orphan")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="investigation", cascade="all, delete-orphan")
    evidence_artifacts: Mapped[list["EvidenceArtifact"]] = relationship("EvidenceArtifact", back_populates="investigation", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="investigation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_investigations_workspace_created", "workspace_id", "created_at"),
        Index("ix_investigations_workspace_status", "workspace_id", "status"),
    )


class InvestigationScope(Base):
    __tablename__ = "investigation_scopes"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_targets: Mapped[Any] = mapped_column(get_json_type(), default=list, nullable=False)  # list of allowed domains, hosts, IPs
    allowed_operations: Mapped[Any] = mapped_column(get_json_type(), default=list, nullable=False)  # list of permitted capabilities
    denied_targets: Mapped[Any] = mapped_column(get_json_type(), default=list, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="scope")

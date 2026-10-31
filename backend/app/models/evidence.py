import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.core.database import Base, GUID, get_json_type


class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    tool_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("tool_runs.id", ondelete="SET NULL"), nullable=True)

    storage_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), default="text/html", nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_locator: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    collected_by: Mapped[str] = mapped_column(String(100), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    integrity_status: Mapped[str] = mapped_column(String(50), default="verified", nullable=False)
    retention_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=90),
        nullable=False
    )
    metadata_json: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    investigation: Mapped["Investigation"] = sa_relationship("Investigation", back_populates="evidence_artifacts")
    sources: Mapped[list["FindingSource"]] = sa_relationship("FindingSource", back_populates="evidence_artifact", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_evidence_investigation_collected", "investigation_id", "collected_at"),
        Index("ix_evidence_workspace_sha", "workspace_id", "sha256"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    finding_type: Mapped[str] = mapped_column(String(100), nullable=False)  # domain_info, tech_stack, contact, metadata, credential_leak
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="unreviewed", nullable=False)  # unreviewed, supported, contradicted, insufficient_evidence, rejected
    confidence_level: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)  # low, medium, high
    confidence_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, default=1.0, nullable=True)

    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processor_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    derived_from: Mapped[Any] = mapped_column(get_json_type(), default=list, nullable=False)  # references to raw inputs

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    investigation: Mapped["Investigation"] = sa_relationship("Investigation", back_populates="findings")
    sources: Mapped[list["FindingSource"]] = sa_relationship("FindingSource", back_populates="finding", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_findings_investigation_type", "investigation_id", "finding_type"),
        Index("ix_findings_investigation_status", "investigation_id", "verification_status"),
    )


class FindingSource(Base):
    __tablename__ = "finding_sources"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_artifact_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("evidence_artifacts.id", ondelete="CASCADE"), nullable=False, index=True)

    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_locator: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # DOM selector, file offset, line number
    source_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    relationship: Mapped[str] = mapped_column(String(100), default="supports", nullable=False)  # supports, contradicts, contextualizes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    finding: Mapped["Finding"] = sa_relationship("Finding", back_populates="sources")
    evidence_artifact: Mapped["EvidenceArtifact"] = sa_relationship("EvidenceArtifact", back_populates="sources")

    __table_args__ = (
        UniqueConstraint("finding_id", "evidence_artifact_id", "source_locator", name="uq_finding_source_locator"),
    )

import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, get_json_type


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # domain, ip, organization, person, email, repository
    display_label: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    attributes_json: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)

    source_entity_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)  # resolves_to, hosted_on, affiliated_with, authored_by
    direction: Mapped[str] = mapped_column(String(20), default="directed", nullable=False)  # directed, bidirectional
    evidence_finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("findings.id", ondelete="SET NULL"), nullable=True)
    confidence_level: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)  # low, medium, high

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    source_entity: Mapped["Entity"] = relationship("Entity", foreign_keys=[source_entity_id])
    target_entity: Mapped["Entity"] = relationship("Entity", foreign_keys=[target_entity_id])

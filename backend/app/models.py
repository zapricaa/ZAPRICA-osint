import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, Enum as SAEnum,
    ForeignKey, Boolean, Integer, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


class InvestigationStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EntityType(str, enum.Enum):
    DOMAIN = "domain"
    IP_ADDRESS = "ip_address"
    URL = "url"
    EMAIL = "email"
    PERSON = "person"
    ORGANIZATION = "organization"
    FILE_HASH = "file_hash"
    PHONE = "phone"
    ASN = "asn"
    CERTIFICATE = "certificate"


class RelationshipType(str, enum.Enum):
    RESOLVES_TO = "resolves_to"
    ASSOCIATED_WITH = "associated_with"
    MENTIONS = "mentions"
    HOSTS = "hosts"
    REGISTERED_BY = "registered_by"
    ISSUED_TO = "issued_to"
    CONTAINS = "contains"
    SUBDOMAIN_OF = "subdomain_of"
    PART_OF = "part_of"


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    seed_entity = Column(String(512), nullable=False)
    seed_entity_type = Column(SAEnum(EntityType), nullable=False)
    status = Column(SAEnum(InvestigationStatus), default=InvestigationStatus.DRAFT)
    authorized_use_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    config = Column(JSON, nullable=True)

    entities = relationship("Entity", back_populates="investigation", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="investigation", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="investigation", cascade="all, delete-orphan")
    relationships = relationship("EntityRelationship", back_populates="investigation", cascade="all, delete-orphan")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String, primary_key=True, default=gen_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    entity_type = Column(SAEnum(EntityType), nullable=False)
    value = Column(String(2048), nullable=False)
    normalized_value = Column(String(2048), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    source = Column(String(512), nullable=True)
    confidence = Column(String(50), default="observed")
    first_seen = Column(DateTime(timezone=True), default=utcnow)
    last_seen = Column(DateTime(timezone=True), default=utcnow)

    investigation = relationship("Investigation", back_populates="entities")


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id = Column(String, primary_key=True, default=gen_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    source_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    target_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    relationship_type = Column(SAEnum(RelationshipType), nullable=False)
    confidence = Column(String(50), default="observed")
    evidence_id = Column(String, ForeignKey("evidence.id"), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    investigation = relationship("Investigation", back_populates="relationships")
    source_entity = relationship("Entity", foreign_keys=[source_entity_id])
    target_entity = relationship("Entity", foreign_keys=[target_entity_id])
    evidence = relationship("Evidence", foreign_keys=[evidence_id])


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=gen_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    source_url = Column(String(2048), nullable=True)
    tool_name = Column(String(255), nullable=True)
    collection_method = Column(String(255), nullable=True)
    content_type = Column(String(255), nullable=True)
    raw_content = Column(Text, nullable=True)
    sha256_hash = Column(String(64), nullable=True)
    storage_ref = Column(String(1024), nullable=True)
    collected_at = Column(DateTime(timezone=True), default=utcnow)
    status = Column(String(50), default="collected")

    investigation = relationship("Investigation", back_populates="evidence_items")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    action = Column(String(255), nullable=False)
    actor = Column(String(255), default="system")
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow)

    investigation = relationship("Investigation", back_populates="activity_logs")


class ToolDefinition(Base):
    __tablename__ = "tool_definitions"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    input_schema = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True)
    requires_network = Column(Boolean, default=True)
    risk_level = Column(String(50), default="low")
    created_at = Column(DateTime(timezone=True), default=utcnow)

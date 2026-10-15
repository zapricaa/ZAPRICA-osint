from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# --- Investigation Schemas ---

class InvestigationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    seed_entity: str = Field(..., min_length=1, max_length=512)
    seed_entity_type: str = Field(..., pattern="^(domain|ip_address|url|email|person|organization|file_hash|phone|asn|certificate)$")
    authorized_use_confirmed: bool = False
    config: Optional[dict] = None


class InvestigationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|active|paused|completed|failed|cancelled)$")
    config: Optional[dict] = None


class InvestigationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    seed_entity: str
    seed_entity_type: str
    status: str
    authorized_use_confirmed: bool
    created_at: datetime
    updated_at: datetime
    entity_count: int = 0
    evidence_count: int = 0

    model_config = {"from_attributes": True}


class InvestigationListResponse(BaseModel):
    investigations: List[InvestigationResponse]
    total: int


# --- Entity Schemas ---

class EntityCreate(BaseModel):
    entity_type: str
    value: str = Field(..., min_length=1, max_length=2048)
    source: Optional[str] = None
    metadata: Optional[dict] = None


class EntityResponse(BaseModel):
    id: str
    investigation_id: str
    entity_type: str
    value: str
    normalized_value: str
    source: Optional[str]
    confidence: str
    first_seen: datetime
    last_seen: datetime
    metadata: Optional[dict] = None

    model_config = {"from_attributes": True}


# --- Relationship Schemas ---

class RelationshipCreate(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: str = "observed"
    evidence_id: Optional[str] = None
    metadata: Optional[dict] = None


class RelationshipResponse(BaseModel):
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: str
    evidence_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Evidence Schemas ---

class EvidenceCreate(BaseModel):
    source_url: Optional[str] = None
    tool_name: Optional[str] = None
    collection_method: Optional[str] = None
    content_type: Optional[str] = None
    raw_content: Optional[str] = None


class EvidenceResponse(BaseModel):
    id: str
    investigation_id: str
    source_url: Optional[str]
    tool_name: Optional[str]
    collection_method: Optional[str]
    content_type: Optional[str]
    sha256_hash: Optional[str]
    storage_ref: Optional[str]
    collected_at: datetime
    status: str

    model_config = {"from_attributes": True}


# --- Activity Log Schemas ---

class ActivityLogResponse(BaseModel):
    id: str
    investigation_id: str
    action: str
    actor: str
    details: Optional[dict]
    timestamp: datetime

    model_config = {"from_attributes": True}


# --- Tool Registry Schemas ---

class ToolResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    input_schema: Optional[dict]
    enabled: bool
    requires_network: bool
    risk_level: str

    model_config = {"from_attributes": True}


class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: dict = {}
    investigation_id: Optional[str] = None


class ToolExecuteResponse(BaseModel):
    success: bool
    tool_name: str
    result: Optional[Any] = None
    error: Optional[str] = None
    evidence_id: Optional[str] = None
    entities_found: int = 0


# --- Graph Schemas ---

class GraphNode(BaseModel):
    id: str
    label: str
    entity_type: str
    value: str
    confidence: str
    metadata: Optional[dict] = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: str
    confidence: str
    evidence_id: Optional[str] = None


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# --- Health / Status ---

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    services: dict

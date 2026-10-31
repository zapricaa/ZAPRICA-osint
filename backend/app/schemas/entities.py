import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


# Tasks
class TaskOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    investigation_id: uuid.UUID
    parent_task_id: Optional[uuid.UUID] = None
    requesting_agent: str
    assigned_agent: str
    capability: str
    objective: str
    status: str
    risk_class: str
    input_json: Any
    expected_output_schema: str
    allowed_tool_ids: List[str]
    attempt_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Evidence
class EvidenceArtifactOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    investigation_id: uuid.UUID
    task_id: Optional[uuid.UUID] = None
    storage_uri: str
    media_type: str
    byte_size: int
    sha256: str
    source_locator: Optional[str] = None
    source_url: Optional[str] = None
    collected_by: str
    collected_at: datetime
    integrity_status: str
    metadata_json: Any
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Finding Source
class FindingSourceOut(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    evidence_artifact_id: uuid.UUID
    source_url: Optional[str] = None
    source_locator: Optional[str] = None
    source_title: Optional[str] = None
    observed_at: datetime
    relationship: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Finding
class FindingOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    investigation_id: uuid.UUID
    task_id: Optional[uuid.UUID] = None
    finding_type: str
    title: str
    normalized_value: Optional[str] = None
    summary: str
    verification_status: str
    confidence_level: str
    confidence_reason: Optional[str] = None
    relevance_score: Optional[float] = None
    first_observed_at: datetime
    last_observed_at: datetime
    processor_name: Optional[str] = None
    processor_version: Optional[str] = None
    derived_from: Any
    created_at: datetime
    updated_at: datetime
    sources: List[FindingSourceOut] = []

    model_config = ConfigDict(from_attributes=True)


class FindingListOut(BaseModel):
    items: List[FindingOut]
    total: int
    page: int
    page_size: int


# Report
class ReportOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    investigation_id: uuid.UUID
    version: int
    status: str
    title: str
    summary: str
    report_json: Any
    artifact_id: Optional[uuid.UUID] = None
    created_by_agent: str
    reviewed_by: Optional[uuid.UUID] = None
    created_at: datetime
    finalized_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

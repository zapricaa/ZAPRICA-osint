"""Pydantic Schemas for DCE Collectors, Structured Findings, and Job Requests."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.collection.contracts import CollectorType, TargetType, CollectorStatus


# --- 1. WHOIS Schemas ---

class WhoisResult(BaseModel):
    domain: str
    registrar: Optional[str] = None
    creation_date: Optional[str] = None
    expiration_date: Optional[str] = None
    updated_date: Optional[str] = None
    name_servers: List[str] = Field(default_factory=list)
    registrant_organization: Optional[str] = None
    raw_text: str = ""
    is_redacted: bool = False
    status_flags: List[str] = Field(default_factory=list)


# --- 2. DNS Schemas ---

class DnsRecordItem(BaseModel):
    record_type: str  # A, AAAA, MX, NS, TXT, CNAME, SOA, CAA
    value: str
    ttl: Optional[int] = None
    priority: Optional[int] = None


class DnsQueryResult(BaseModel):
    domain: str
    query_types: List[str] = Field(default_factory=list)
    records: List[DnsRecordItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    query_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- 3. HIBP Schemas ---

class HibpBreachItem(BaseModel):
    name: str
    title: str
    domain: str
    breach_date: str
    added_date: Optional[str] = None
    pwn_count: int = 0
    data_classes: List[str] = Field(default_factory=list)
    is_verified: bool = False
    is_fabricated: bool = False
    is_sensitive: bool = False


class HibpLookupResult(BaseModel):
    email: str
    breaches: List[HibpBreachItem] = Field(default_factory=list)
    breach_count: int = 0
    status: str = "ok"


# --- 4. theHarvester Schemas ---

class TheHarvesterResult(BaseModel):
    domain: str
    subdomains: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    sources_used: List[str] = Field(default_factory=list)


# --- 5. Sherlock Schemas ---

class SherlockProfileItem(BaseModel):
    site_name: str
    profile_url: str
    is_candidate: bool = True  # Explicit disclaimer: username similarity is not proof of identity


class SherlockResult(BaseModel):
    username: str
    candidates: List[SherlockProfileItem] = Field(default_factory=list)
    total_candidates: int = 0
    disclaimer: str = "Candidate profile matches only. Public username reuse is an investigative indicator, not proof of individual identity."


# --- 6. Holehe Schemas ---

class HoleheAccountItem(BaseModel):
    service_name: str
    domain: str
    account_exists: bool = True


class HoleheResult(BaseModel):
    email: str
    registered_services: List[HoleheAccountItem] = Field(default_factory=list)
    rate_limit_encountered: bool = False
    policy_status: str = "restricted"


# --- 7. Synthetic Demo Schemas ---

class DemoResult(BaseModel):
    identifier: str
    target_type: str
    is_synthetic: bool = True
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    disclaimer: str = "SYNTHETIC DEMO DATA ONLY. No real external networks or individuals were queried."


# --- 8. DCE Job Submission and Capability Schemas ---

class CollectionJobRequest(BaseModel):
    investigation_id: uuid.UUID
    tool_id: str
    target: str
    target_type: TargetType
    options: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = None


class CollectionJobResponse(BaseModel):
    job_id: str
    investigation_id: uuid.UUID
    tool_id: str
    target: str
    target_type: TargetType
    status: CollectorStatus
    execution_duration_ms: int = 0
    evidence_artifact_id: Optional[uuid.UUID] = None
    evidence_sha256: Optional[str] = None
    finding_ids: List[uuid.UUID] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class CollectorCapabilityInfo(BaseModel):
    tool_id: str
    name: str
    description: str
    collector_type: CollectorType
    supported_target_types: List[TargetType]
    is_enabled: bool
    requires_approval: bool
    requires_api_key: bool
    is_available: bool
    availability_note: str = ""


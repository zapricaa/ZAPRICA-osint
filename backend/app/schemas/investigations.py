import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


class InvestigationScopeCreate(BaseModel):
    purpose: str = Field(..., min_length=5, max_length=1000)
    allowed_targets: List[str] = Field(..., min_length=1, description="List of allowlisted domains/hosts")
    allowed_operations: List[str] = Field(
        default=["public_website_metadata", "content_extraction"],
        description="Permitted capability identifiers"
    )
    denied_targets: List[str] = Field(default=[], description="Explicitly denied targets/subnets")
    expires_at: Optional[datetime] = None


class InvestigationScopeOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    workspace_id: uuid.UUID
    purpose: str
    allowed_targets: List[str]
    allowed_operations: List[str]
    denied_targets: List[str]
    expires_at: datetime
    policy_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    objective: str = Field(..., min_length=5, max_length=2000)
    investigation_type: str = Field(default="public_website", max_length=100)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    scope: InvestigationScopeCreate


class InvestigationOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: Optional[uuid.UUID]
    title: str
    objective: str
    investigation_type: str
    status: str
    priority: str
    plan_json: Optional[Any] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retention_until: datetime
    created_at: datetime
    updated_at: datetime
    scope: Optional[InvestigationScopeOut] = None

    model_config = ConfigDict(from_attributes=True)


class InvestigationListOut(BaseModel):
    items: List[InvestigationOut]
    total: int
    page: int
    page_size: int


class InvestigationActionResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str
    action_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

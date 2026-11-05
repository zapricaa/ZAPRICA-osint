import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class InvestigationScopeCreate(BaseModel):
    purpose: str = Field(default="OSINT Investigation Scope", min_length=3, max_length=1000)
    allowed_targets: List[str] = Field(..., min_length=1, description="List of allowlisted domains/hosts")
    allowed_operations: List[str] = Field(
        default=["public_website_metadata", "content_extraction"],
        description="Permitted capability identifiers"
    )
    denied_targets: List[str] = Field(default=[], description="Explicitly denied targets/subnets")
    expires_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_scope_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("allowed_targets") and data.get("allowlist"):
                data["allowed_targets"] = data["allowlist"]
            if not data.get("denied_targets") and data.get("denylist"):
                data["denied_targets"] = data["denylist"]
            if not data.get("purpose"):
                data["purpose"] = "OSINT Investigation Scope"
        return data


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
    objective: str = Field(..., min_length=3, max_length=2000)
    investigation_type: str = Field(default="public_website", max_length=100)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    scope: InvestigationScopeCreate

    @model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("objective") and data.get("description"):
                data["objective"] = data["description"]
            elif not data.get("objective") and data.get("target"):
                data["objective"] = f"Investigation on {data['target']}"
            if not data.get("investigation_type") and data.get("target_type"):
                data["investigation_type"] = str(data["target_type"]).lower()
            if "scope" in data and isinstance(data["scope"], dict):
                if not data["scope"].get("purpose"):
                    data["scope"]["purpose"] = data.get("objective") or "Investigation Scope"
                if not data["scope"].get("allowed_targets"):
                    if data["scope"].get("allowlist"):
                        data["scope"]["allowed_targets"] = data["scope"]["allowlist"]
                    elif data.get("target"):
                        data["scope"]["allowed_targets"] = [data["target"]]
        return data


class InvestigationOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: Optional[uuid.UUID]
    title: str
    target: Optional[str] = None
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

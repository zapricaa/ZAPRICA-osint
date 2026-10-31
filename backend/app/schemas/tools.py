import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ToolDraftCreate(BaseModel):
    tool_key: str = Field(..., min_length=2, max_length=100)
    display_name: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=10, max_length=2000)
    vendor_or_source: str = Field(..., max_length=255)
    license_id: str = Field(default="MIT", max_length=100)
    homepage_url: Optional[str] = None
    version: str = Field(default="1.0.0", max_length=50)
    execution_type: str = Field(default="library", pattern="^(browser|terminal|api|library)$")
    capabilities: List[str] = Field(default=["generic_recon"])
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    documentation_text: Optional[str] = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class ToolVersionOut(BaseModel):
    id: uuid.UUID
    tool_id: uuid.UUID
    version: str
    execution_type: str
    capabilities: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    manifest_json: Dict[str, Any]
    playbook_markdown: str
    approval_status: str
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    timeout_seconds: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolSummary(BaseModel):
    id: uuid.UUID
    tool_key: str
    display_name: str
    description: str
    vendor_or_source: str
    license_id: str
    status: str
    active_version: Optional[str] = None
    execution_type: Optional[str] = None
    capabilities: List[str] = []
    approval_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ToolAssignmentCreate(BaseModel):
    agent_type: str = Field(..., pattern="^(browser_head|terminal_head|worker)$")
    capability: str
    enabled: bool = True
    scope_constraints: Dict[str, Any] = Field(default_factory=dict)


class ToolAssignmentOut(BaseModel):
    id: uuid.UUID
    tool_version_id: uuid.UUID
    agent_type: str
    capability: str
    enabled: bool
    scope_constraints: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ToolValidationOut(BaseModel):
    version_id: uuid.UUID
    approval_status: str
    tests_passed: bool
    validation_details: Dict[str, Any]

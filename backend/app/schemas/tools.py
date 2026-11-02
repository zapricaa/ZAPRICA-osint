import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ToolDraftCreate(BaseModel):
    tool_key: Optional[str] = Field(None, min_length=2, max_length=100)
    display_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: str = Field(..., min_length=5, max_length=2000)
    vendor_or_source: Optional[str] = Field(None, max_length=255)
    license_id: str = Field(default="MIT", max_length=100)
    homepage_url: Optional[str] = None
    version: str = Field(default="1.0.0", max_length=50)
    execution_type: str = Field(default="library", pattern="^(browser|terminal|api|library)$")
    capabilities: List[str] = Field(default=["generic_recon"])
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    documentation_text: Optional[str] = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            name = data.get("name")
            if name:
                if not data.get("tool_key"):
                    data["tool_key"] = name.lower().replace(" ", "_").replace("-", "_")
                if not data.get("display_name"):
                    data["display_name"] = name
            elif not data.get("display_name") and data.get("tool_key"):
                data["display_name"] = data["tool_key"]
            elif not data.get("tool_key") and data.get("display_name"):
                data["tool_key"] = data["display_name"].lower().replace(" ", "_").replace("-", "_")

            if not data.get("vendor_or_source"):
                data["vendor_or_source"] = "Custom / Operator"

            exec_type = data.get("execution_type", "library")
            if isinstance(exec_type, str):
                exec_type_lower = exec_type.lower()
                if exec_type_lower in ("container", "docker", "cli"):
                    data["execution_type"] = "terminal"
                elif exec_type_lower in ("browser", "terminal", "api", "library"):
                    data["execution_type"] = exec_type_lower
                else:
                    data["execution_type"] = "library"
        return data


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
    name: Optional[str] = None
    version: Optional[str] = None
    risk_level: str = "LOW"
    timeout_seconds: int = 30

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_frontend_aliases(self) -> "ToolSummary":
        if not self.name:
            self.name = self.display_name or self.tool_key
        if not self.version:
            self.version = self.active_version or "1.0.0"
        return self


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

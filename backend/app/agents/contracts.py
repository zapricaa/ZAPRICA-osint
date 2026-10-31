from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid


class TaskEnvelope(BaseModel):
    schema_version: str = "1.0"
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    parent_task_id: Optional[str] = None
    requesting_agent: str = "main_head"
    assigned_agent: str  # browser_head, terminal_head, worker
    capability: str
    objective: str
    scope_ref: str
    allowed_tool_ids: List[str] = []
    input: Dict[str, Any] = {}
    expected_output_schema: str = "generic_result.v1"
    risk_class: str = "low"
    budget: Dict[str, int] = Field(default_factory=lambda: {"max_tool_calls": 5, "max_runtime_seconds": 60})
    deadline: Optional[str] = None
    idempotency_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkerResultEnvelope(BaseModel):
    schema_version: str = "1.0"
    task_id: str
    agent_id: str
    status: str = "succeeded"  # succeeded, no_findings, partial, failed, timed_out
    outcome: str = "findings_returned"
    findings: List[Dict[str, Any]] = []
    evidence_refs: List[str] = []
    tool_run_refs: List[str] = []
    warnings: List[str] = []
    error: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(from_attributes=True)


class FindingsPackage(BaseModel):
    schema_version: str = "1.0"
    investigation_id: str
    subhead_agent: str  # browser_head, terminal_head
    status: str = "succeeded"  # succeeded, partial, no_findings, failed
    findings: List[Dict[str, Any]] = []
    evidence_artifacts: List[Dict[str, Any]] = []
    execution_summary: Dict[str, Any] = {}
    warnings: List[str] = []

    model_config = ConfigDict(from_attributes=True)

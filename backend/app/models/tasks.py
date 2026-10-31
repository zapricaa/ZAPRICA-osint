import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, get_json_type


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    requesting_agent: Mapped[str] = mapped_column(String(100), default="main_head", nullable=False)
    assigned_agent: Mapped[str] = mapped_column(String(100), nullable=False)  # browser_head, terminal_head, worker
    capability: Mapped[str] = mapped_column(String(100), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)  # queued, running, awaiting_approval, succeeded, no_findings, partial, failed, timed_out, cancelled
    risk_class: Mapped[str] = mapped_column(String(50), default="low", nullable=False)  # low, medium, high, critical
    input_json: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    expected_output_schema: Mapped[str] = mapped_column(String(100), default="generic_result.v1", nullable=False)
    allowed_tool_ids: Mapped[Any] = mapped_column(get_json_type(), default=list, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    budget_json: Mapped[Any] = mapped_column(get_json_type(), default=lambda: {"max_tool_calls": 5, "max_runtime_seconds": 60}, nullable=False)
    deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="tasks")
    parent_task: Mapped[Optional["Task"]] = relationship("Task", remote_side="Task.id", back_populates="subtasks")
    subtasks: Mapped[list["Task"]] = relationship("Task", back_populates="parent_task")
    agent_runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="task", cascade="all, delete-orphan")
    tool_runs: Mapped[list["ToolRun"]] = relationship("ToolRun", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tasks_investigation_status", "investigation_id", "status"),
        Index("ix_tasks_assigned_status", "assigned_agent", "status"),
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)  # main_head, browser_head, terminal_head, worker
    model_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_microunits: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(100), default=lambda: str(uuid.uuid4()), nullable=False)
    error_json: Mapped[Optional[Any]] = mapped_column(get_json_type(), nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="agent_runs")


class ToolRun(Base):
    __tablename__ = "tool_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_version_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("tool_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    agent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)

    requested_by_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)  # running, succeeded, failed, timed_out, denied
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    validated_input_json: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    output_artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    policy_decision_id: Mapped[str] = mapped_column(String(100), default=lambda: str(uuid.uuid4()), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(100), default=lambda: str(uuid.uuid4()), nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="tool_runs")
    tool_version: Mapped["ToolVersion"] = relationship("ToolVersion", back_populates="tool_runs")

import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, get_json_type


class TerminalEnvironment(Base):
    """Isolated container execution environment for terminal tasks."""
    __tablename__ = "terminal_environments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    environment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    image_name: Mapped[str] = mapped_column(String(255), default="zaprica-sandbox:latest", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="STOPPED", nullable=False)  # STOPPED, STARTING, READY, BUSY, ERROR
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    resource_limits: Mapped[Any] = mapped_column(get_json_type(), default=lambda: {"cpu_limit": "1.0", "memory_limit": "512m"}, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    sessions: Mapped[list["TerminalSession"]] = relationship("TerminalSession", back_populates="environment", cascade="all, delete-orphan")


class TerminalSession(Base):
    """Active or historical Docker container run session."""
    __tablename__ = "terminal_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    environment_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("terminal_environments.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    container_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="IDLE", nullable=False)  # IDLE, RUNNING, COMPLETED, FAILED, TIMED_OUT

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    environment: Mapped["TerminalEnvironment"] = relationship("TerminalEnvironment", back_populates="sessions")
    terminal_tasks: Mapped[list["TerminalTask"]] = relationship("TerminalTask", back_populates="session", cascade="all, delete-orphan")


class TerminalTask(Base):
    """Specific task executed in isolated container runtime."""
    __tablename__ = "terminal_tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("terminal_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    tool_id: Mapped[str] = mapped_column(String(100), nullable=False)
    command_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    validated_arguments: Mapped[Any] = mapped_column(get_json_type(), default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED", nullable=False)  # QUEUED, RUNNING, COMPLETED, FAILED, BLOCKED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[Optional["TerminalSession"]] = relationship("TerminalSession", back_populates="terminal_tasks")
    logs: Mapped[list["TerminalExecutionLog"]] = relationship("TerminalExecutionLog", back_populates="terminal_task", cascade="all, delete-orphan")


class TerminalExecutionLog(Base):
    """Real-time stdout, stderr, and resource metrics for a terminal execution."""
    __tablename__ = "terminal_execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    terminal_task_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("terminal_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resource_usage: Mapped[Optional[Any]] = mapped_column(get_json_type(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    terminal_task: Mapped["TerminalTask"] = relationship("TerminalTask", back_populates="logs")

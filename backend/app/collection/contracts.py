"""DCE (Data Collection Engine) Contracts and Core Types."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field


class CollectorType(str, Enum):
    CLI = "cli"
    API = "api"
    SYNTHETIC = "synthetic"


class TargetType(str, Enum):
    DOMAIN = "domain"
    IP = "ip"
    EMAIL = "email"
    USERNAME = "username"
    # Note: Phone number support is strictly prohibited and not invented per requirements.


class CollectorStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class RawCollectorOutput(BaseModel):
    """Raw output package captured from a collector execution before evidence persistence."""
    tool_id: str
    tool_version: str = "1.0.0"
    status: CollectorStatus
    target: str
    target_type: TargetType
    raw_bytes: bytes = b""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_duration_ms: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    parsed_data: Dict[str, Any] = Field(default_factory=dict)
    is_synthetic: bool = False
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


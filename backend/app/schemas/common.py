from typing import Optional, Any
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Short error code / title")
    detail: str = Field(..., description="Human-readable description of error")
    status_code: int
    trace_id: Optional[str] = None
    validation_errors: Optional[Any] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    dependencies: Optional[dict] = None

"""Model configuration for ZAPRICA AI Brain."""

from typing import Optional
from pydantic import BaseModel, Field
from app.core.config import settings


class ModelConfig(BaseModel):
    """Runtime model configuration parsed from environment settings."""

    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: settings.GEMINI_API_KEY
    )
    default_model: str = Field(
        default_factory=lambda: settings.GEMINI_MODEL or "gemini-3.8-flash"
    )
    main_head_model: str = Field(
        default_factory=lambda: settings.GEMINI_MAIN_HEAD_MODEL or "gemini-3.8-flash"
    )
    browser_head_model: str = Field(
        default_factory=lambda: settings.GEMINI_BROWSER_HEAD_MODEL or "gemini-3.5-flash-lite"
    )
    terminal_head_model: str = Field(
        default_factory=lambda: settings.GEMINI_TERMINAL_HEAD_MODEL or "gemini-3.5-flash-lite"
    )
    timeout_seconds: int = 45
    max_retries: int = 3
    retry_base_delay: float = 1.0
    temperature: float = 0.2


# Singleton configuration instance
model_config = ModelConfig()

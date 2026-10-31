"""Abstract base class and exceptions for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel
from app.ai.schemas.reasoning import ProposedToolCall

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(Exception):
    """Base exception for LLM provider failures."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when the LLM call exceeds the configured timeout."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when the LLM provider rate limits the request (HTTP 429)."""
    pass


class LLMValidationError(LLMProviderError):
    """Raised when the LLM output cannot be validated against the requested Pydantic schema."""
    pass


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers in ZAPRICA."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate unstructured text from the LLM."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """Generate structured data strictly validated against a Pydantic schema."""
        pass

    @abstractmethod
    async def propose_tool_call(
        self,
        prompt: str,
        available_tools: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[ProposedToolCall]:
        """Ask LLM to select and parameterize an approved tool from available TIMS tools."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider credentials and network connectivity are operational."""
        pass

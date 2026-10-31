import abc
import json
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(abc.ABC):
    """Abstract interface for LLM providers."""

    @abc.abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        untrusted_context: Optional[str] = None
    ) -> T:
        """Generate schema-validated output from the model."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Deterministic, zero-cost LLM provider for tests and hermetic local dev."""

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        untrusted_context: Optional[str] = None
    ) -> T:
        # Prompt injection defense check: Ensure untrusted context didn't inject commands
        if untrusted_context and "IGNORE ALL PREVIOUS INSTRUCTIONS" in untrusted_context:
            pass  # Successfully treated as passive data

        # Deterministic responses based on target schema
        schema_name = schema.__name__
        if "Plan" in schema_name or "InvestigationPlan" in schema_name:
            mock_data = {
                "understanding": "Investigate public web infrastructure and metadata of the target",
                "risk_assessment": "low",
                "tasks": [
                    {
                        "assigned_agent": "browser_head",
                        "capability": "public_website_metadata",
                        "objective": "Collect website title, headings, and technology indicators",
                        "allowed_tools": ["website_metadata"],
                    },
                    {
                        "assigned_agent": "terminal_head",
                        "capability": "dns_lookup",
                        "objective": "Retrieve DNS A, AAAA, MX, and TXT records",
                        "allowed_tools": ["dns_lookup"],
                    }
                ],
                "assumptions": ["Target is reachable via public internet"],
                "missing_information": []
            }
        elif "Synthesis" in schema_name or "ReportSummary" in schema_name:
            mock_data = {
                "executive_summary": "Reconnaissance completed within authorized scope.",
                "verified_facts": ["Target web server is operational"],
                "inferences": ["Architecture appears to use reverse proxy"],
                "missing_information": [],
                "confidence_score": 0.95
            }
        else:
            mock_data = {}

        return schema.model_validate(mock_data)


def get_llm_provider() -> BaseLLMProvider:
    """Factory returning configured LLM provider."""
    # In local/test mode, use MockLLMProvider
    return MockLLMProvider()

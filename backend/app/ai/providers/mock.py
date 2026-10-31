"""Hermetic mock LLM provider for automated testing and offline development."""

import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from app.ai.providers.base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)
from app.ai.schemas.reasoning import (
    BrowserTaskDecompositionSchema,
    ExecutiveSummarySchema,
    FindingsAnalysisSchema,
    FollowUpDecisionSchema,
    InvestigationObjectiveAnalysis,
    InvestigationPlanSchema,
    PlannedTaskSchema,
    ProposedToolCall,
    TerminalTaskDecompositionSchema,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(BaseLLMProvider):
    """Deterministic, hermetic mock provider for offline tests and validation."""

    def __init__(
        self,
        canned_responses: Optional[Dict[str, Any]] = None,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_validation_error: bool = False,
        simulate_server_error: bool = False,
    ):
        self.canned_responses = canned_responses or {}
        self.simulate_timeout = simulate_timeout
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_validation_error = simulate_validation_error
        self.simulate_server_error = simulate_server_error
        self.call_history: List[Dict[str, Any]] = []

    def _check_simulated_failures(self):
        if self.simulate_timeout:
            raise LLMTimeoutError("Simulated timeout: LLM provider timed out after 30s")
        if self.simulate_rate_limit:
            raise LLMRateLimitError("Simulated rate limit: HTTP 429 Resource Exhausted")
        if self.simulate_validation_error:
            raise LLMValidationError("Simulated validation error: Output failed schema constraints")
        if self.simulate_server_error:
            raise LLMProviderError("Simulated server error: HTTP 500 Internal Server Error")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        self.call_history.append(
            {"type": "text", "prompt": prompt, "system_instruction": system_instruction, "model": model}
        )
        self._check_simulated_failures()

        if "text" in self.canned_responses:
            return str(self.canned_responses["text"])
        return f"Mock reasoning response for: {prompt[:80]}"

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        self.call_history.append(
            {
                "type": "structured",
                "schema": response_schema.__name__,
                "prompt": prompt,
                "system_instruction": system_instruction,
                "model": model,
            }
        )
        self._check_simulated_failures()

        schema_name = response_schema.__name__
        if schema_name in self.canned_responses:
            data = self.canned_responses[schema_name]
            if isinstance(data, response_schema):
                return data
            return response_schema.model_validate(data)

        # Generate realistic default structured responses based on schema type
        if response_schema is InvestigationObjectiveAnalysis:
            return response_schema(  # type: ignore
                target_type="domain",
                primary_identifier="example.com",
                scope_compliance_verified=True,
                identified_objectives=["Domain registration discovery", "DNS mapping", "Web intelligence"],
                risk_assessment="Passive reconnaissance, low risk of detection",
            )

        if response_schema is InvestigationPlanSchema:
            return response_schema(  # type: ignore
                summary="Execute multi-source OSINT correlation on the target identifier.",
                tasks=[
                    PlannedTaskSchema(
                        title="DNS and Infrastructure Reconnaissance",
                        description="Resolve DNS records and network topology.",
                        assigned_agent="terminal_head",
                        priority=1,
                        suggested_tools=["dns_lookup"],
                        required_inputs={"domain": "example.com"},
                    ),
                    PlannedTaskSchema(
                        title="WHOIS Registration Inspection",
                        description="Query domain registrar and contact records.",
                        assigned_agent="terminal_head",
                        priority=2,
                        suggested_tools=["whois_lookup"],
                        required_inputs={"domain": "example.com"},
                    ),
                    PlannedTaskSchema(
                        title="Public Web Surface Extraction",
                        description="Extract landing page headers, metadata, and linked entities.",
                        assigned_agent="browser_head",
                        priority=3,
                        suggested_tools=["playwright_extract"],
                        required_inputs={"url": "https://example.com"},
                    ),
                ],
                rationale="Begin with passive network and registration reconnaissance before web scraping.",
            )

        if response_schema is BrowserTaskDecompositionSchema:
            return response_schema(  # type: ignore
                worker_type="web_research",
                action="extract_page_metadata",
                target_url_or_query="https://example.com",
                expected_data_type="html_metadata_and_links",
                parameters={"extract_links": True, "timeout": 30},
            )

        if response_schema is TerminalTaskDecompositionSchema:
            return response_schema(  # type: ignore
                worker_type="network_intel",
                tool_name="dns_lookup",
                tool_parameters={"domain": "example.com", "record_types": ["A", "MX", "NS"]},
                rationale="Identify hosting infrastructure and mail exchanges",
            )

        if response_schema is ProposedToolCall:
            return response_schema(  # type: ignore
                tool_name="dns_lookup",
                arguments={"domain": "example.com"},
                justification="Need to identify target nameservers and primary IP address.",
            )

        if response_schema is FindingsAnalysisSchema:
            return response_schema(  # type: ignore
                observed_facts=[
                    "Target domain resolves to 93.184.216.34",
                    "Domain registrar is Internet Assigned Numbers Authority",
                    "Web server returns status HTTP 200 OK",
                ],
                hypotheses_and_inferences=[
                    "Infrastructure appears to be reserved documentation IP space",
                    "No production email servers configured on apex domain",
                ],
                identified_conflicts=[],
                identified_gaps=["No subdomains enumerated yet"],
                confidence_score=0.95,
            )

        if response_schema is FollowUpDecisionSchema:
            return response_schema(  # type: ignore
                investigation_complete=True,
                completion_reason="All primary investigation objectives satisfied within approved scope.",
                follow_up_tasks=[],
            )

        if response_schema is ExecutiveSummarySchema:
            return response_schema(  # type: ignore
                title="OSINT Investigation Summary for example.com",
                key_findings=[
                    "Domain resolved to static IPv4 address",
                    "Registrar details confirmed active",
                    "Public landing page successfully indexed with verified provenance hash",
                ],
                threat_level="info",
                evidence_summary="Gathered 3 raw evidence artifacts with valid SHA-256 integrity hashes.",
                recommended_actions=["Monitor for DNS changes", "Archive current evidence bundle"],
            )

        # Fallback empty model validation
        return response_schema.model_validate({})

    async def propose_tool_call(
        self,
        prompt: str,
        available_tools: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[ProposedToolCall]:
        self.call_history.append(
            {
                "type": "propose_tool_call",
                "prompt": prompt,
                "available_tools": [t.get("name") for t in available_tools],
                "model": model,
            }
        )
        self._check_simulated_failures()

        if "ProposedToolCall" in self.canned_responses:
            data = self.canned_responses["ProposedToolCall"]
            if isinstance(data, ProposedToolCall):
                return data
            return ProposedToolCall.model_validate(data)

        # Pick first tool if available
        if available_tools:
            tool = available_tools[0]
            return ProposedToolCall(
                tool_name=tool.get("name", "dns_lookup"),
                arguments={"domain": "example.com"},
                justification="Appropriate for initial domain intelligence gathering.",
            )
        return None

    async def is_available(self) -> bool:
        return True

"""High-level AI Reasoning Service for ZAPRICA Multi-Agent System."""

import logging
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from app.ai.model_registry import registry
from app.ai.prompts.system_prompts import (
    BROWSER_HEAD_SYSTEM_PROMPT,
    FINDINGS_SYNTHESIS_PROMPT,
    MAIN_HEAD_SYSTEM_PROMPT,
    TERMINAL_HEAD_SYSTEM_PROMPT,
    WRAP_UNTRUSTED_DATA,
)
from app.ai.providers.base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMValidationError,
)
from app.ai.schemas.reasoning import (
    BrowserTaskDecompositionSchema,
    ExecutiveSummarySchema,
    FindingsAnalysisSchema,
    FollowUpDecisionSchema,
    InvestigationObjectiveAnalysis,
    InvestigationPlanSchema,
    ProposedToolCall,
    TerminalTaskDecompositionSchema,
)

logger = logging.getLogger(__name__)


class LLMService:
    """Orchestrates structured reasoning across Main Head, Browser Head, and Terminal Head."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self._provider = provider

    @property
    def provider(self) -> BaseLLMProvider:
        if self._provider is None:
            return registry.get_provider()
        return self._provider

    async def analyze_objective(
        self,
        target: str,
        user_prompt: str,
        allowlist: Optional[List[str]] = None,
        denylist: Optional[List[str]] = None,
    ) -> InvestigationObjectiveAnalysis:
        """Main Head: Analyze user request, verify scope compliance, and extract objectives."""
        allowlist = allowlist or []
        denylist = denylist or []

        prompt = (
            f"Analyze the following investigation target and user objective.\n"
            f"TARGET: {target}\n"
            f"USER PROMPT: {user_prompt}\n"
            f"ALLOWED TARGETS: {allowlist}\n"
            f"DENIED TARGETS: {denylist}\n\n"
            f"Check if the target violates any denylist rules. Extract the target type, primary identifier, "
            f"granular OSINT objectives, and risk assessment."
        )

        model = registry.get_model_for_role("main_head")
        return await self.provider.generate_structured(
            prompt=prompt,
            response_schema=InvestigationObjectiveAnalysis,
            system_instruction=MAIN_HEAD_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,
        )

    async def create_investigation_plan(
        self,
        target: str,
        objective_analysis: InvestigationObjectiveAnalysis,
        available_tools: Optional[List[Dict[str, Any]]] = None,
        context_history: Optional[List[Dict[str, Any]]] = None,
    ) -> InvestigationPlanSchema:
        """Main Head: Generate structured investigation plan with decomposed tasks."""
        available_tools = available_tools or []
        tools_summary = ", ".join(t.get("name", "") for t in available_tools if t.get("name"))

        history_summary = ""
        if context_history:
            history_summary = f"\nPREVIOUS TASK HISTORY:\n{context_history}\n"

        prompt = (
            f"Generate a rigorous investigation plan for target: {target}\n"
            f"Target Type: {objective_analysis.target_type}\n"
            f"Objectives: {objective_analysis.identified_objectives}\n"
            f"Risk Assessment: {objective_analysis.risk_assessment}\n"
            f"Available Registered Tools: {tools_summary}\n"
            f"{history_summary}\n"
            f"Sequence tasks logically (e.g. passive network recon with terminal_head first, then web surface analysis with browser_head). "
            f"Assign each task strictly to 'browser_head' or 'terminal_head'."
        )

        model = registry.get_model_for_role("main_head")
        return await self.provider.generate_structured(
            prompt=prompt,
            response_schema=InvestigationPlanSchema,
            system_instruction=MAIN_HEAD_SYSTEM_PROMPT,
            model=model,
            temperature=0.2,
        )

    async def decompose_browser_task(
        self,
        task_title: str,
        task_description: str,
        parameters: Dict[str, Any],
    ) -> BrowserTaskDecompositionSchema:
        """Browser Head: Decompose browser task into specific worker instructions."""
        prompt = (
            f"Decompose the following browser task for execution:\n"
            f"Task Title: {task_title}\n"
            f"Task Description: {task_description}\n"
            f"Parameters: {parameters}\n\n"
            f"Determine the appropriate browser worker type, action, target URL/query, and expected data."
        )

        model = registry.get_model_for_role("browser_head")
        return await self.provider.generate_structured(
            prompt=prompt,
            response_schema=BrowserTaskDecompositionSchema,
            system_instruction=BROWSER_HEAD_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,
        )

    async def decompose_terminal_task(
        self,
        task_title: str,
        task_description: str,
        parameters: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
    ) -> TerminalTaskDecompositionSchema:
        """Terminal Head: Select approved tool and formulate structured parameters."""
        tool_names = [t.get("name") for t in available_tools if t.get("name")]
        prompt = (
            f"Decompose the following terminal task for execution:\n"
            f"Task Title: {task_title}\n"
            f"Task Description: {task_description}\n"
            f"Parameters: {parameters}\n"
            f"Approved TIMS Tools Available: {tool_names}\n\n"
            f"Select an approved tool and provide validated parameters. Do not output raw shell commands."
        )

        model = registry.get_model_for_role("terminal_head")
        return await self.provider.generate_structured(
            prompt=prompt,
            response_schema=TerminalTaskDecompositionSchema,
            system_instruction=TERMINAL_HEAD_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,
        )

    async def synthesize_findings(
        self,
        findings: List[Dict[str, Any]],
        evidence_artifacts: Optional[List[Dict[str, Any]]] = None,
    ) -> FindingsAnalysisSchema:
        """Main Head: Correlate findings, separate facts from inferences, and detect conflicts."""
        evidence_artifacts = evidence_artifacts or []

        findings_blob = WRAP_UNTRUSTED_DATA(
            str(findings), source_label="worker_findings_and_evidence"
        )

        prompt = (
            f"Review the following collected intelligence findings and raw evidence:\n\n"
            f"{findings_blob}\n\n"
            f"Synthesize the findings. List observed facts that are grounded in evidence. "
            f"List analytical inferences separately. Identify any cross-source discrepancies or gaps."
        )

        model = registry.get_model_for_role("main_head")
        return await self.provider.generate_structured(
            prompt=prompt,
            response_schema=FindingsAnalysisSchema,
            system_instruction=FINDINGS_SYNTHESIS_PROMPT,
            model=model,
            temperature=0.2,
        )

    async def evaluate_completion(
        self,
        objectives: List[str],
        findings_analysis: FindingsAnalysisSchema,
        completed_tasks_count: int,
        max_task_budget: int = 10,
    ) -> FollowUpDecisionSchema:
        """Main Head: Determine if objectives are satisfied or if follow-up tasks are needed."""
        prompt = (
            f"Determine if the investigation is complete.\n"
            f"Objectives: {objectives}\n"
            f"Identified Facts: {findings_analysis.observed_facts}\n"
            f"Identified Gaps: {findings_analysis.identified_gaps}\n"
            f"Completed Tasks: {completed_tasks_count} / {max_task_budget}\n\n"
            f"If all primary objectives are addressed or if budget is exhausted, mark complete. "
            f"Otherwise, propose specific follow-up tasks."
        )

        model = registry.get_model_for_role("main_head")
        return await self.provider.generate_structured(
            prompt=prompt,
            response_schema=FollowUpDecisionSchema,
            system_instruction=MAIN_HEAD_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,
        )

    async def generate_executive_summary(
        self,
        investigation_title: str,
        target: str,
        findings_analysis: FindingsAnalysisSchema,
    ) -> ExecutiveSummarySchema:
        """Main Head: Generate final executive summary for the investigation report."""
        prompt = (
            f"Generate a professional executive summary for investigation '{investigation_title}' (Target: {target}).\n"
            f"Observed Facts: {findings_analysis.observed_facts}\n"
            f"Inferences: {findings_analysis.hypotheses_and_inferences}\n"
            f"Conflicts: {findings_analysis.identified_conflicts}\n"
            f"Confidence Score: {findings_analysis.confidence_score}\n"
        )

        model = registry.get_model_for_role("main_head")
        return await self.provider.generate_structured(
            prompt=prompt,
            response_schema=ExecutiveSummarySchema,
            system_instruction=MAIN_HEAD_SYSTEM_PROMPT,
            model=model,
            temperature=0.2,
        )


# Global AI reasoning service instance
llm_service = LLMService()

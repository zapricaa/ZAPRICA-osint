"""Holehe Collector Adapter: Optional email registration checker with strict disabled-by-default policy."""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Set, Optional, List
from fastapi import HTTPException

from app.collection.adapters.base import BaseCollectorAdapter
from app.collection.contracts import CollectorType, TargetType, CollectorStatus, RawCollectorOutput
from app.collection.schemas import HoleheAccountItem, HoleheResult
from app.core.config import settings
from app.terminal.terminal_manager import terminal_manager
from app.terminal.sandbox_manager import DockerSandboxManager


class HoleheCollectorAdapter(BaseCollectorAdapter):
    """Optional Holehe Email Registration Indicator Adapter (Disabled by Default)."""

    @property
    def tool_id(self) -> str:
        return "holehe"

    @property
    def name(self) -> str:
        return "Holehe Registered Account Indicator (Restricted)"

    @property
    def description(self) -> str:
        return "Checks whether an email address is registered on major platforms without alerting the target. Restricted & disabled by default."

    @property
    def collector_type(self) -> CollectorType:
        return CollectorType.CLI

    @property
    def supported_target_types(self) -> Set[TargetType]:
        return {TargetType.EMAIL}

    @property
    def requires_approval(self) -> bool:
        return True

    def is_available(self) -> Tuple[bool, str]:
        if not settings.HOLEHE_ENABLED:
            return False, "Holehe adapter is disabled by policy. Administrator review and explicit activation required."
        if not DockerSandboxManager.is_docker_available():
            return False, "Docker sandbox daemon is offline"
        return True, ""

    def validate_target(self, target: str) -> None:
        email = target.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) or email.startswith("-"):
            raise HTTPException(status_code=400, detail=f"Invalid email address format for Holehe query: '{target}'")

    def _parse_holehe_output(self, email: str, text: str) -> HoleheResult:
        registered: List[HoleheAccountItem] = []
        rate_limited = "rate limit" in text.lower() or "429" in text

        # Matches lines like: [+] domain.com
        pattern = re.compile(r"\[\+\]\s+([A-Za-z0-9.\-]+\.[a-z]{2,})", re.IGNORECASE)
        for match in pattern.finditer(text):
            dom = match.group(1).strip().lower()
            service_name = dom.split(".")[0].capitalize()
            registered.append(HoleheAccountItem(
                service_name=service_name,
                domain=dom,
                account_exists=True,
            ))

        return HoleheResult(
            email=email,
            registered_services=registered,
            rate_limit_encountered=rate_limited,
            policy_status="active" if settings.HOLEHE_ENABLED else "disabled",
        )

    async def execute(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> RawCollectorOutput:
        self.validate_target(target)
        email = target.strip().lower()
        t_id = task_id or f"holehe-{uuid.uuid4().hex[:8]}"

        # Enforce disabled-by-default policy check
        if not settings.HOLEHE_ENABLED:
            return RawCollectorOutput(
                tool_id=self.tool_id,
                tool_version="1.0.0",
                status=CollectorStatus.DISABLED,
                target=email,
                target_type=TargetType.EMAIL,
                raw_bytes=b"{}",
                stdout="",
                stderr="Holehe is disabled by default in ZAPRICA configuration.",
                warnings=["Holehe adapter is disabled by policy until privacy and licensing review is completed."],
                errors=["Tool execution rejected: disabled policy."],
                parsed_data={"email": email, "registered_services": [], "policy_status": "disabled"},
                is_synthetic=False,
                collected_at=datetime.now(timezone.utc),
            )

        start_time = time.monotonic()
        exec_res = await terminal_manager.execute_task(
            task_id=t_id,
            tool_id=self.tool_id,
            arguments={"email": email},
            timeout_seconds=120,
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)

        raw_output_text = (exec_res.stdout or "") + ("\n" + exec_res.stderr if exec_res.stderr else "")
        raw_bytes = raw_output_text.encode("utf-8")

        warnings = []
        errors = []
        status = CollectorStatus.SUCCESS if exec_res.exit_code == 0 else CollectorStatus.FAILED

        if exec_res.exit_code != 0:
            errors.append(f"holehe exited with code {exec_res.exit_code}: {exec_res.stderr[:200]}")

        parsed_result = self._parse_holehe_output(email, raw_output_text)

        if parsed_result.rate_limit_encountered:
            warnings.append("Rate limit encountered on one or more external service endpoints during lookup.")

        return RawCollectorOutput(
            tool_id=self.tool_id,
            tool_version="1.0.0",
            status=status,
            target=email,
            target_type=TargetType.EMAIL,
            raw_bytes=raw_bytes,
            stdout=exec_res.stdout,
            stderr=exec_res.stderr,
            exit_code=exec_res.exit_code,
            execution_duration_ms=duration_ms,
            warnings=warnings,
            errors=errors,
            parsed_data=parsed_result.model_dump(),
            is_synthetic=False,
            collected_at=datetime.now(timezone.utc),
        )


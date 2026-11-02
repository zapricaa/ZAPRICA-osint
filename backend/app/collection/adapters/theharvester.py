"""theHarvester Collector Adapter: Collects public domain subdomains and emails via Docker sandbox."""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Set, Optional, List
from fastapi import HTTPException

from app.collection.adapters.base import BaseCollectorAdapter
from app.collection.contracts import CollectorType, TargetType, CollectorStatus, RawCollectorOutput
from app.collection.schemas import TheHarvesterResult
from app.terminal.terminal_manager import terminal_manager
from app.terminal.sandbox_manager import DockerSandboxManager


class TheHarvesterCollectorAdapter(BaseCollectorAdapter):
    """theHarvester public domain intelligence collector executing in Docker sandbox."""

    @property
    def tool_id(self) -> str:
        return "theharvester"

    @property
    def name(self) -> str:
        return "theHarvester Domain Intelligence"

    @property
    def description(self) -> str:
        return "Gathers public subdomains and email addresses from passive public data sources (e.g. Certificate Transparency)."

    @property
    def collector_type(self) -> CollectorType:
        return CollectorType.CLI

    @property
    def supported_target_types(self) -> Set[TargetType]:
        return {TargetType.DOMAIN}

    def is_available(self) -> Tuple[bool, str]:
        if not DockerSandboxManager.is_docker_available():
            return False, "Docker sandbox daemon is offline"
        return True, ""

    def validate_target(self, target: str) -> None:
        t = target.strip().lower()
        if "://" in t:
            t = t.split("://", 1)[1].split("/", 1)[0]
        if not re.match(r"^[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", t) or t.startswith("-"):
            raise HTTPException(status_code=400, detail=f"Invalid domain format for theHarvester: '{target}'")

    def _parse_theharvester_output(self, domain: str, text: str, sources: List[str]) -> TheHarvesterResult:
        subdomains: List[str] = []
        emails: List[str] = []

        # Find emails matching the domain
        email_pattern = re.compile(r"\b[A-Za-z0-9._%+\-]+@" + re.escape(domain) + r"\b", re.IGNORECASE)
        for em in email_pattern.findall(text):
            em_lower = em.lower()
            if em_lower not in emails:
                emails.append(em_lower)

        # Find subdomains matching *.domain
        subdomain_pattern = re.compile(r"\b(?:[A-Za-z0-9\-]+\.)+" + re.escape(domain) + r"\b", re.IGNORECASE)
        for sub in subdomain_pattern.findall(text):
            sub_lower = sub.lower()
            if sub_lower != domain and "@" not in sub_lower and sub_lower not in subdomains:
                subdomains.append(sub_lower)

        return TheHarvesterResult(
            domain=domain,
            subdomains=sorted(subdomains),
            emails=sorted(emails),
            sources_used=sources,
        )

    async def execute(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> RawCollectorOutput:
        self.validate_target(target)
        opts = options or {}
        t_id = task_id or f"harvester-{uuid.uuid4().hex[:8]}"

        domain = target.strip().lower()
        if "://" in domain:
            domain = domain.split("://", 1)[1].split("/", 1)[0]

        sources = str(opts.get("sources", "crtsh")).strip()
        limit = int(opts.get("limit", 200))

        start_time = time.monotonic()
        exec_res = await terminal_manager.execute_task(
            task_id=t_id,
            tool_id=self.tool_id,
            arguments={"domain": domain, "sources": sources, "limit": limit},
            timeout_seconds=120,
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)

        raw_output_text = (exec_res.stdout or "") + ("\n" + exec_res.stderr if exec_res.stderr else "")
        raw_bytes = raw_output_text.encode("utf-8")

        warnings = []
        errors = []
        status = CollectorStatus.SUCCESS if exec_res.exit_code == 0 else CollectorStatus.FAILED

        if exec_res.exit_code != 0:
            errors.append(f"theHarvester exited with code {exec_res.exit_code}: {exec_res.stderr[:200]}")

        sources_list = [s.strip() for s in sources.split(",") if s.strip()]
        parsed_result = self._parse_theharvester_output(domain, raw_output_text, sources_list)

        if not parsed_result.subdomains and not parsed_result.emails:
            warnings.append(f"theHarvester discovered 0 subdomains and 0 emails for '{domain}'.")

        return RawCollectorOutput(
            tool_id=self.tool_id,
            tool_version="1.0.0",
            status=status,
            target=domain,
            target_type=TargetType.DOMAIN,
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


"""Sherlock Collector Adapter: Searches for public username profile candidates via Docker sandbox."""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Set, Optional, List
from fastapi import HTTPException

from app.collection.adapters.base import BaseCollectorAdapter
from app.collection.contracts import CollectorType, TargetType, CollectorStatus, RawCollectorOutput
from app.collection.schemas import SherlockProfileItem, SherlockResult
from app.terminal.terminal_manager import terminal_manager
from app.terminal.sandbox_manager import DockerSandboxManager


class SherlockCollectorAdapter(BaseCollectorAdapter):
    """Sherlock Public Username Profile Collector executing in Docker sandbox."""

    @property
    def tool_id(self) -> str:
        return "sherlock"

    @property
    def name(self) -> str:
        return "Sherlock Username Profile Hunter"

    @property
    def description(self) -> str:
        return "Discovers candidate public profile URLs associated with a username across online services."

    @property
    def collector_type(self) -> CollectorType:
        return CollectorType.CLI

    @property
    def supported_target_types(self) -> Set[TargetType]:
        return {TargetType.USERNAME}

    def is_available(self) -> Tuple[bool, str]:
        if not DockerSandboxManager.is_docker_available():
            return False, "Docker sandbox daemon is offline"
        return True, ""

    def validate_target(self, target: str) -> None:
        u = target.strip()
        if not re.match(r"^[a-zA-Z0-9_\-\.]{2,64}$", u) or u.startswith("-"):
            raise HTTPException(status_code=400, detail=f"Invalid username format for Sherlock query: '{target}'")

    def _parse_sherlock_output(self, username: str, text: str) -> SherlockResult:
        candidates: List[SherlockProfileItem] = []
        # Matches patterns like: [+] Twitter: https://twitter.com/target
        pattern = re.compile(r"\[\+\]\s+([^:]+):\s+(https?://\S+)", re.IGNORECASE)

        for match in pattern.finditer(text):
            site_name = match.group(1).strip()
            profile_url = match.group(2).strip()
            candidates.append(SherlockProfileItem(
                site_name=site_name,
                profile_url=profile_url,
                is_candidate=True,
            ))

        return SherlockResult(
            username=username,
            candidates=candidates,
            total_candidates=len(candidates),
        )

    async def execute(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> RawCollectorOutput:
        self.validate_target(target)
        opts = options or {}
        username = target.strip()
        t_id = task_id or f"sherlock-{uuid.uuid4().hex[:8]}"

        site_timeout = str(opts.get("timeout", "10")).strip()

        start_time = time.monotonic()
        exec_res = await terminal_manager.execute_task(
            task_id=t_id,
            tool_id=self.tool_id,
            arguments={"username": username, "timeout": site_timeout},
            timeout_seconds=120,
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)

        raw_output_text = (exec_res.stdout or "") + ("\n" + exec_res.stderr if exec_res.stderr else "")
        raw_bytes = raw_output_text.encode("utf-8")

        warnings = []
        errors = []
        status = CollectorStatus.SUCCESS if exec_res.exit_code == 0 else CollectorStatus.FAILED

        if exec_res.exit_code != 0:
            errors.append(f"sherlock exited with code {exec_res.exit_code}: {exec_res.stderr[:200]}")

        parsed_result = self._parse_sherlock_output(username, raw_output_text)

        if not parsed_result.candidates:
            warnings.append(f"No public profile candidates discovered for username '{username}'.")

        return RawCollectorOutput(
            tool_id=self.tool_id,
            tool_version="1.0.0",
            status=status,
            target=username,
            target_type=TargetType.USERNAME,
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


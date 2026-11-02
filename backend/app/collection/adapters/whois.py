"""WHOIS Collector Adapter: Executes native Linux WHOIS in Docker sandbox and parses RFC 3912 data."""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Set, Optional, List
from fastapi import HTTPException

from app.collection.adapters.base import BaseCollectorAdapter
from app.collection.contracts import CollectorType, TargetType, CollectorStatus, RawCollectorOutput
from app.collection.schemas import WhoisResult
from app.terminal.terminal_manager import terminal_manager
from app.terminal.sandbox_manager import DockerSandboxManager


class WhoisCollectorAdapter(BaseCollectorAdapter):
    """WHOIS Domain Registration Collector executing via Docker isolation."""

    @property
    def tool_id(self) -> str:
        return "whois_lookup"

    @property
    def name(self) -> str:
        return "WHOIS Domain Registration Lookup"

    @property
    def description(self) -> str:
        return "Queries public registry WHOIS servers for domain ownership, registrar, creation, and expiration dates."

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
            raise HTTPException(status_code=400, detail=f"Invalid domain format for WHOIS query: '{target}'")

    def _parse_whois_output(self, domain: str, text: str) -> WhoisResult:
        """Parses raw RFC 3912 text output into a structured WhoisResult."""
        registrar = None
        creation_date = None
        expiration_date = None
        updated_date = None
        registrant_org = None
        name_servers: List[str] = []
        status_flags: List[str] = []
        is_redacted = False

        # Key mapping normalization
        key_patterns = {
            "registrar": re.compile(r"^\s*registrar:\s*(.+)$", re.IGNORECASE),
            "creation_date": re.compile(r"^\s*(creation date|created|registration time):\s*(.+)$", re.IGNORECASE),
            "expiration_date": re.compile(r"^\s*(registry expiry date|registrar registration expiration date|expiry date|expiration time|paid-till):\s*(.+)$", re.IGNORECASE),
            "updated_date": re.compile(r"^\s*(updated date|last updated|last-modified):\s*(.+)$", re.IGNORECASE),
            "registrant_org": re.compile(r"^\s*(registrant organization|registrant org|org-name):\s*(.+)$", re.IGNORECASE),
            "name_server": re.compile(r"^\s*(name server|nserver):\s*(.+)$", re.IGNORECASE),
            "domain_status": re.compile(r"^\s*(domain status|status):\s*(.+)$", re.IGNORECASE),
        }

        redaction_indicators = ["redacted", "privacy", "gdpr", "withheld", "not disclosed", "protected"]

        for line in text.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("%") or line_str.startswith("#"):
                continue

            # Check for privacy redaction flags
            if any(ind in line_str.lower() for ind in redaction_indicators):
                is_redacted = True

            # Registrar
            if not registrar:
                m = key_patterns["registrar"].match(line_str)
                if m:
                    registrar = m.group(1).strip()
                    continue

            # Creation date
            if not creation_date:
                m = key_patterns["creation_date"].match(line_str)
                if m:
                    creation_date = m.group(2).strip()
                    continue

            # Expiration date
            if not expiration_date:
                m = key_patterns["expiration_date"].match(line_str)
                if m:
                    expiration_date = m.group(2).strip()
                    continue

            # Updated date
            if not updated_date:
                m = key_patterns["updated_date"].match(line_str)
                if m:
                    updated_date = m.group(2).strip()
                    continue

            # Registrant Organization
            if not registrant_org:
                m = key_patterns["registrant_org"].match(line_str)
                if m:
                    registrant_org = m.group(2).strip()
                    continue

            # Name Servers
            m = key_patterns["name_server"].match(line_str)
            if m:
                ns = m.group(2).strip().lower().split()[0]
                if ns not in name_servers:
                    name_servers.append(ns)
                continue

            # Domain Status
            m = key_patterns["domain_status"].match(line_str)
            if m:
                st = m.group(2).strip().split()[0]
                if st not in status_flags:
                    status_flags.append(st)
                continue

        return WhoisResult(
            domain=domain,
            registrar=registrar,
            creation_date=creation_date,
            expiration_date=expiration_date,
            updated_date=updated_date,
            name_servers=name_servers,
            registrant_organization=registrant_org,
            raw_text=text,
            is_redacted=is_redacted,
            status_flags=status_flags,
        )

    async def execute(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> RawCollectorOutput:
        self.validate_target(target)
        t_id = task_id or f"whois-{uuid.uuid4().hex[:8]}"

        domain = target.strip().lower()
        if "://" in domain:
            domain = domain.split("://", 1)[1].split("/", 1)[0]

        start_time = time.monotonic()
        # Execute in hardened Docker container via TerminalManager
        exec_res = await terminal_manager.execute_task(
            task_id=t_id,
            tool_id=self.tool_id,
            arguments={"target": domain},
            timeout_seconds=30,
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)

        raw_output_text = (exec_res.stdout or "") + ("\n" + exec_res.stderr if exec_res.stderr else "")
        raw_bytes = raw_output_text.encode("utf-8")

        warnings = []
        errors = []
        status = CollectorStatus.SUCCESS if exec_res.exit_code == 0 else CollectorStatus.FAILED

        # Detect not found / lookup failures
        if "No match for" in raw_output_text or "NOT FOUND" in raw_output_text or "Status: free" in raw_output_text:
            warnings.append(f"Domain '{domain}' does not appear to be currently registered.")

        if exec_res.exit_code != 0:
            errors.append(f"whois exited with code {exec_res.exit_code}: {exec_res.stderr[:200]}")

        parsed_whois = self._parse_whois_output(domain, raw_output_text)

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
            parsed_data=parsed_whois.model_dump(),
            is_synthetic=False,
            collected_at=datetime.now(timezone.utc),
        )


"""DNS Collector Adapter: Executes native Linux dig in Docker sandbox and parses full record suites."""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Set, Optional, List
from fastapi import HTTPException

from app.collection.adapters.base import BaseCollectorAdapter
from app.collection.contracts import CollectorType, TargetType, CollectorStatus, RawCollectorOutput
from app.collection.schemas import DnsRecordItem, DnsQueryResult
from app.terminal.terminal_manager import terminal_manager
from app.terminal.sandbox_manager import DockerSandboxManager


class DnsCollectorAdapter(BaseCollectorAdapter):
    """DNS Intelligence Collector querying full record suites via dig in Docker container."""

    SUPPORTED_RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA"]

    @property
    def tool_id(self) -> str:
        return "dns_lookup"

    @property
    def name(self) -> str:
        return "DNS Full Record Enumerator (dig)"

    @property
    def description(self) -> str:
        return "Collects DNS records (A, AAAA, MX, NS, TXT, CNAME, SOA, CAA) using native Linux dig."

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
            raise HTTPException(status_code=400, detail=f"Invalid domain format for DNS query: '{target}'")

    def _parse_record_lines(self, rtype: str, raw_text: str) -> List[DnsRecordItem]:
        """Parses output lines from dig +short for specific record type."""
        records: List[DnsRecordItem] = []
        for line in raw_text.splitlines():
            clean = line.strip()
            if not clean or clean.startswith(";") or clean.startswith(";;"):
                continue

            if rtype == "MX":
                parts = clean.split(maxsplit=1)
                if len(parts) == 2 and parts[0].isdigit():
                    records.append(DnsRecordItem(
                        record_type="MX",
                        value=parts[1].rstrip("."),
                        priority=int(parts[0])
                    ))
                else:
                    records.append(DnsRecordItem(record_type="MX", value=clean.rstrip(".")))

            elif rtype == "TXT":
                # Strip wrapping quotes from TXT strings
                val = clean.strip('"')
                records.append(DnsRecordItem(record_type="TXT", value=val))

            elif rtype in ("A", "AAAA", "NS", "CNAME", "SOA", "CAA"):
                records.append(DnsRecordItem(record_type=rtype, value=clean.rstrip(".")))

        return records

    async def execute(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> RawCollectorOutput:
        self.validate_target(target)
        opts = options or {}
        t_id = task_id or f"dns-{uuid.uuid4().hex[:8]}"

        domain = target.strip().lower()
        if "://" in domain:
            domain = domain.split("://", 1)[1].split("/", 1)[0]

        # Determine which record types to query
        requested_types = opts.get("record_types")
        if not requested_types:
            single_type = opts.get("record_type")
            if single_type and single_type in self.SUPPORTED_RECORD_TYPES:
                types_to_query = [single_type]
            else:
                types_to_query = self.SUPPORTED_RECORD_TYPES
        else:
            types_to_query = [rt.upper() for rt in requested_types if rt.upper() in self.SUPPORTED_RECORD_TYPES]

        start_time = time.monotonic()
        all_records: List[DnsRecordItem] = []
        combined_stdout = []
        warnings: List[str] = []
        errors: List[str] = []

        overall_exit_code = 0

        for rtype in types_to_query:
            try:
                exec_res = await terminal_manager.execute_task(
                    task_id=f"{t_id}-{rtype.lower()}",
                    tool_id=self.tool_id,
                    arguments={"target": domain, "record_type": rtype},
                    timeout_seconds=15,
                )
                if exec_res.stdout:
                    combined_stdout.append(f";; QUERY TYPE: {rtype}\n{exec_res.stdout}")
                    records = self._parse_record_lines(rtype, exec_res.stdout)
                    all_records.extend(records)
                if exec_res.exit_code != 0:
                    overall_exit_code = exec_res.exit_code
                    errors.append(f"dig {rtype} query failed with code {exec_res.exit_code}")
            except Exception as e:
                warnings.append(f"Failed to query DNS record type {rtype}: {str(e)}")

        duration_ms = int((time.monotonic() - start_time) * 1000)
        raw_text = "\n".join(combined_stdout)
        raw_bytes = raw_text.encode("utf-8")

        if not all_records and not errors:
            warnings.append(f"No DNS records found for domain '{domain}' across queried types {types_to_query}.")

        query_result = DnsQueryResult(
            domain=domain,
            query_types=types_to_query,
            records=all_records,
            warnings=warnings,
            query_timestamp=datetime.now(timezone.utc),
        )

        status = CollectorStatus.SUCCESS if all_records or (not errors) else CollectorStatus.FAILED

        return RawCollectorOutput(
            tool_id=self.tool_id,
            tool_version="1.0.0",
            status=status,
            target=domain,
            target_type=TargetType.DOMAIN,
            raw_bytes=raw_bytes,
            stdout=raw_text,
            stderr="\n".join(errors),
            exit_code=overall_exit_code,
            execution_duration_ms=duration_ms,
            warnings=warnings,
            errors=errors,
            parsed_data=query_result.model_dump(),
            is_synthetic=False,
            collected_at=datetime.now(timezone.utc),
        )


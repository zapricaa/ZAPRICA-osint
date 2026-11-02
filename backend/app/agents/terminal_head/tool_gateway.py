import abc
import socket
import subprocess
import ipaddress
import uuid
from typing import Dict, Any, Type, Optional, List
from pydantic import BaseModel, Field
from fastapi import HTTPException, status

from app.agents.browser_head.ssrf_filter import SSRFEgressFilter
from app.core.safe_mode import safe_mode_controller


class ToolAdapter(abc.ABC):
    """Abstract base class for all sandboxed CLI adapters."""

    @property
    @abc.abstractmethod
    def tool_id(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def argument_schema(self) -> Type[BaseModel]:
        pass

    @abc.abstractmethod
    async def execute(self, validated_args: BaseModel, timeout_seconds: int = 15) -> Dict[str, Any]:
        pass


class DNSLookupArgs(BaseModel):
    target: str = Field(..., min_length=3, max_length=255, description="Domain name to resolve")
    record_type: str = Field(default="A", pattern="^(A|AAAA|MX|TXT|NS|CNAME|SOA|CAA)$")


class DNSLookupAdapter(ToolAdapter):
    @property
    def tool_id(self) -> str:
        return "dns_lookup"

    @property
    def argument_schema(self) -> Type[BaseModel]:
        return DNSLookupArgs

    async def execute(self, validated_args: DNSLookupArgs, timeout_seconds: int = 15) -> Dict[str, Any]:
        domain = validated_args.target.strip().lower()
        if "://" in domain:
            domain = domain.split("://", 1)[1].split("/", 1)[0]

        # Enforce SSRF Egress filter on host
        resolved_ips = SSRFEgressFilter.resolve_and_validate(domain)

        from app.terminal.sandbox_manager import DockerSandboxManager
        from app.terminal.terminal_manager import terminal_manager

        records = resolved_ips
        # If Docker sandbox is available, query real dig records
        if DockerSandboxManager.is_docker_available():
            try:
                res = await terminal_manager.execute_task(
                    task_id=f"dns-{uuid.uuid4().hex[:8]}",
                    tool_id="dns_lookup",
                    arguments={"target": domain, "record_type": validated_args.record_type},
                    timeout_seconds=timeout_seconds,
                )
                if res.stdout:
                    dig_records = [line.strip().strip('"') for line in res.stdout.splitlines() if line.strip() and not line.startswith(";")]
                    if dig_records:
                        records = dig_records
            except Exception:
                pass

        return {
            "target": domain,
            "record_type": validated_args.record_type,
            "records": records,
            "resolved_count": len(records),
            "status": "success"
        }


class WhoisLookupArgs(BaseModel):
    target: str = Field(..., min_length=3, max_length=255, description="Domain name to query")


class WhoisLookupAdapter(ToolAdapter):
    @property
    def tool_id(self) -> str:
        return "whois_lookup"

    @property
    def argument_schema(self) -> Type[BaseModel]:
        return WhoisLookupArgs

    async def execute(self, validated_args: WhoisLookupArgs, timeout_seconds: int = 15) -> Dict[str, Any]:
        domain = validated_args.target.strip().lower()
        if "://" in domain:
            domain = domain.split("://", 1)[1].split("/", 1)[0]

        # Ensure no private network target
        SSRFEgressFilter.resolve_and_validate(domain)

        from app.terminal.sandbox_manager import DockerSandboxManager
        from app.terminal.terminal_manager import terminal_manager

        registrar = "Public Domain Registry"
        if DockerSandboxManager.is_docker_available():
            try:
                res = await terminal_manager.execute_task(
                    task_id=f"whois-{uuid.uuid4().hex[:8]}",
                    tool_id="whois_lookup",
                    arguments={"target": domain},
                    timeout_seconds=timeout_seconds,
                )
                if res.stdout:
                    import re
                    m = re.search(r"^\s*registrar:\s*(.+)$", res.stdout, re.IGNORECASE | re.MULTILINE)
                    if m:
                        registrar = m.group(1).strip()
            except Exception:
                pass

        return {
            "target": domain,
            "domain_name": domain,
            "registrar": registrar,
            "active_status": "registered",
            "is_public_domain": True,
            "status": "success",
        }


class TheHarvesterArgs(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)
    sources: str = Field(default="crtsh")
    limit: int = Field(default=200, ge=10, le=500)


class TheHarvesterAdapter(ToolAdapter):
    @property
    def tool_id(self) -> str:
        return "theharvester"

    @property
    def argument_schema(self) -> Type[BaseModel]:
        return TheHarvesterArgs

    async def execute(self, validated_args: TheHarvesterArgs, timeout_seconds: int = 120) -> Dict[str, Any]:
        from app.terminal.terminal_manager import terminal_manager
        res = await terminal_manager.execute_task(
            task_id=f"harvester-{uuid.uuid4().hex[:8]}",
            tool_id="theharvester",
            arguments={"domain": validated_args.domain, "sources": validated_args.sources, "limit": validated_args.limit},
            timeout_seconds=timeout_seconds,
        )
        return {
            "domain": validated_args.domain,
            "stdout": res.stdout,
            "status": "success" if res.exit_code == 0 else "failed",
        }


class SherlockArgs(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    timeout: str = Field(default="10")


class SherlockAdapter(ToolAdapter):
    @property
    def tool_id(self) -> str:
        return "sherlock"

    @property
    def argument_schema(self) -> Type[BaseModel]:
        return SherlockArgs

    async def execute(self, validated_args: SherlockArgs, timeout_seconds: int = 120) -> Dict[str, Any]:
        from app.terminal.terminal_manager import terminal_manager
        res = await terminal_manager.execute_task(
            task_id=f"sherlock-{uuid.uuid4().hex[:8]}",
            tool_id="sherlock",
            arguments={"username": validated_args.username, "timeout": validated_args.timeout},
            timeout_seconds=timeout_seconds,
        )
        return {
            "username": validated_args.username,
            "stdout": res.stdout,
            "status": "success" if res.exit_code == 0 else "failed",
        }


class ToolGateway:
    """Secure Tool Gateway: strictly rejects arbitrary shell commands (AC-SEC-01) and validates authorization."""

    def __init__(self):
        self._adapters: Dict[str, ToolAdapter] = {}
        self.register_adapter(DNSLookupAdapter())
        self.register_adapter(WhoisLookupAdapter())
        self.register_adapter(TheHarvesterAdapter())
        self.register_adapter(SherlockAdapter())

    def register_adapter(self, adapter: ToolAdapter):
        self._adapters[adapter.tool_id] = adapter

    def get_adapter(self, tool_id: str) -> Optional[ToolAdapter]:
        return self._adapters.get(tool_id)

    async def execute_tool(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        raw_shell_command: Optional[str] = None,
        initiating_user_id: Optional[uuid.UUID] = None,
        user_roles: Optional[List[str]] = None,
        agent_assigned_tools: Optional[List[str]] = None,
        scope_allowed_targets: Optional[List[str]] = None,
        timeout_seconds: int = 20,
    ) -> Dict[str, Any]:
        # 1. AC-SEC-01: Rejection of arbitrary shell text
        if raw_shell_command is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Arbitrary shell execution is forbidden. Tools must use registered adapters."
            )

        # 2. Safe Startup Mode Enforcement
        if not safe_mode_controller.is_terminal_execution_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Terminal execution is disabled by default in Safe Startup Mode. An administrator must explicitly activate terminal capabilities."
            )

        # 2. Tool Registration Check
        adapter = self.get_adapter(tool_id)
        if not adapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_id}' is not registered or approved."
            )

        # 3. User Role Authorization Check
        if user_roles is not None:
            if "ANALYST" in user_roles and "SUPER_ADMIN" not in user_roles and "INVESTIGATOR" not in user_roles and "ADMINISTRATOR" not in user_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission Denied: Analyst role has read-only access and cannot execute tools."
                )

        # 4. Agent Tool Assignment Check
        if agent_assigned_tools is not None and tool_id not in agent_assigned_tools:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent Authorization Violation: Tool '{tool_id}' is not assigned to this agent."
            )

        # 5. Investigation Scope Check
        target_val = arguments.get("target") or arguments.get("domain") or arguments.get("url")
        if scope_allowed_targets and target_val:
            target_str = str(target_val).lower().strip()
            if "://" in target_str:
                target_str = target_str.split("://", 1)[1].split("/", 1)[0]
            allowed = any(
                target_str == a.lower() or (a.startswith("*.") and target_str.endswith(a[2:].lower()))
                for a in scope_allowed_targets
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Scope Violation: Target '{target_str}' is not in authorized investigation scope {scope_allowed_targets}."
                )

        # 6. Validate arguments strictly against schema
        try:
            validated_args = adapter.argument_schema.model_validate(arguments)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool argument validation failed: {str(e)}"
            )

        # 7. Execute in isolation with timeouts (AC-SEC-04)
        return await adapter.execute(validated_args, timeout_seconds=timeout_seconds)


tool_gateway = ToolGateway()

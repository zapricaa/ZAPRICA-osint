"""Terminal Execution Policy: validates commands, arguments, and prevents arbitrary host command injection."""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException, status


class TerminalCommandSpecification(BaseModel):
    tool_id: str
    command_name: str
    allowed_flags: List[str] = Field(default_factory=list)
    argument_schema: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 30
    requires_network: bool = False
    requires_approval: bool = False


class TerminalExecutionPolicyValidator:
    """Strictly validates CLI commands against registered tool specifications and blocks shell injection."""

    # Disallowed dangerous shell meta-characters and constructs
    DANGEROUS_PATTERNS = [
        re.compile(r"[;&|`$><]"),             # Shell chaining and redirection
        re.compile(r"\b(rm|del|rmdir)\b", re.IGNORECASE),  # Destructive deletes
        re.compile(r"\b(powershell|pwsh|cmd|bash|sh|zsh)\b", re.IGNORECASE), # Shell invocations
        re.compile(r"\b(sudo|su|runas)\b", re.IGNORECASE),  # Privilege escalation
        re.compile(r"\b(curl|wget)\b.*\|", re.IGNORECASE),  # Pipe to shell
        re.compile(r"\.\./"),                 # Path traversal
    ]

    APPROVED_COMMANDS: Dict[str, TerminalCommandSpecification] = {
        "dns_lookup": TerminalCommandSpecification(
            tool_id="dns_lookup",
            command_name="dig",
            allowed_flags=["+short", "+noall", "+answer"],
            timeout_seconds=15,
            requires_network=True,
        ),
        "whois_lookup": TerminalCommandSpecification(
            tool_id="whois_lookup",
            command_name="whois",
            allowed_flags=[],
            timeout_seconds=20,
            requires_network=True,
        ),
        "subdomain_enum": TerminalCommandSpecification(
            tool_id="subdomain_enum",
            command_name="subfinder",
            allowed_flags=["-silent"],
            timeout_seconds=60,
            requires_network=True,
        ),
        "metadata_extractor": TerminalCommandSpecification(
            tool_id="metadata_extractor",
            command_name="exiftool",
            allowed_flags=["-json"],
            timeout_seconds=30,
            requires_network=False,
        ),
        "cert_inspector": TerminalCommandSpecification(
            tool_id="cert_inspector",
            command_name="openssl",
            allowed_flags=["s_client", "-connect", "-showcerts"],
            timeout_seconds=20,
            requires_network=True,
        ),
    }

    @classmethod
    def validate_command(cls, tool_id: str, arguments: Dict[str, Any]) -> TerminalCommandSpecification:
        """Validates that tool_id is approved and arguments do not contain shell injection."""
        spec = cls.APPROVED_COMMANDS.get(tool_id)
        if not spec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Security Policy: Tool '{tool_id}' is not in the approved terminal command allowlist."
            )

        # Inspect all argument values for shell injection patterns
        for key, val in arguments.items():
            val_str = str(val).strip()
            for pattern in cls.DANGEROUS_PATTERNS:
                if pattern.search(val_str):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Security Policy Violation: Argument '{key}' contains disallowed character or command pattern: '{val_str}'"
                    )

        return spec

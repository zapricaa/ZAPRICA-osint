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
            allowed_flags=["+short", "+time=5", "+tries=2"],
            timeout_seconds=15,
            requires_network=True,
        ),
        "whois_lookup": TerminalCommandSpecification(
            tool_id="whois_lookup",
            command_name="whois",
            allowed_flags=[],
            timeout_seconds=30,
            requires_network=True,
        ),
        "theharvester": TerminalCommandSpecification(
            tool_id="theharvester",
            command_name="theHarvester",
            allowed_flags=["-d", "-b", "-l"],
            timeout_seconds=120,
            requires_network=True,
        ),
        "sherlock": TerminalCommandSpecification(
            tool_id="sherlock",
            command_name="sherlock",
            allowed_flags=["--print-found", "--no-color", "--timeout"],
            timeout_seconds=120,
            requires_network=True,
        ),
        "holehe": TerminalCommandSpecification(
            tool_id="holehe",
            command_name="holehe",
            allowed_flags=["--only-used", "--no-color"],
            timeout_seconds=120,
            requires_network=True,
            requires_approval=True,
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
            # Arguments must never start with a hyphen to prevent flag injection
            if key in ("target", "domain", "username", "email") and val_str.startswith("-"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security Policy Violation: Argument '{key}' cannot start with a hyphen (flag injection prevented)."
                )
            for pattern in cls.DANGEROUS_PATTERNS:
                if pattern.search(val_str):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Security Policy Violation: Argument '{key}' contains disallowed character or command pattern: '{val_str}'"
                    )

        return spec

    @classmethod
    def build_argv(cls, tool_id: str, arguments: Dict[str, Any]) -> List[str]:
        """
        Builds a strictly validated, fixed argument vector for an approved tool.
        Never appends raw dictionaries or executes shell strings.
        """
        spec = cls.validate_command(tool_id, arguments)

        if tool_id == "dns_lookup":
            raw_target = str(arguments.get("target") or arguments.get("domain", "")).strip().lower()
            if "://" in raw_target:
                raw_target = raw_target.split("://", 1)[1].split("/", 1)[0]
            if not re.match(r"^[a-zA-Z0-9.\-]+$", raw_target):
                raise HTTPException(status_code=400, detail="Invalid domain format for DNS query.")
            record_type = str(arguments.get("record_type", "A")).upper().strip()
            valid_types = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA"}
            if record_type not in valid_types:
                raise HTTPException(status_code=400, detail=f"Unsupported DNS record type '{record_type}'.")
            return ["dig", "+short", "+time=5", "+tries=2", raw_target, record_type]

        elif tool_id == "whois_lookup":
            raw_target = str(arguments.get("target") or arguments.get("domain", "")).strip().lower()
            if "://" in raw_target:
                raw_target = raw_target.split("://", 1)[1].split("/", 1)[0]
            if not re.match(r"^[a-zA-Z0-9.\-]+$", raw_target):
                raise HTTPException(status_code=400, detail="Invalid domain format for WHOIS query.")
            return ["whois", raw_target]

        elif tool_id == "theharvester":
            raw_domain = str(arguments.get("domain") or arguments.get("target", "")).strip().lower()
            if "://" in raw_domain:
                raw_domain = raw_domain.split("://", 1)[1].split("/", 1)[0]
            if not re.match(r"^[a-zA-Z0-9.\-]+$", raw_domain):
                raise HTTPException(status_code=400, detail="Invalid domain format for theHarvester.")
            sources = str(arguments.get("sources", "crtsh")).strip()
            if not re.match(r"^[a-zA-Z0-9,_\-]+$", sources):
                sources = "crtsh"
            limit = int(arguments.get("limit", 200))
            limit = max(10, min(limit, 500))
            return ["theHarvester", "-d", raw_domain, "-b", sources, "-l", str(limit)]

        elif tool_id == "sherlock":
            username = str(arguments.get("username", "")).strip()
            if not re.match(r"^[a-zA-Z0-9_\-\.]{2,64}$", username) or username.startswith("-"):
                raise HTTPException(status_code=400, detail="Invalid username format for Sherlock.")
            timeout = str(arguments.get("timeout", "10")).strip()
            return ["sherlock", "--print-found", "--no-color", "--timeout", timeout, username]

        elif tool_id == "holehe":
            from app.core.config import settings
            if not settings.HOLEHE_ENABLED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Holehe adapter is disabled by policy. Administrator review and explicit activation required."
                )
            email = str(arguments.get("email", "")).strip().lower()
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
                raise HTTPException(status_code=400, detail="Invalid email format for Holehe.")
            return ["holehe", "--only-used", "--no-color", email]

        elif tool_id == "subdomain_enum":
            raw_target = str(arguments.get("target") or arguments.get("domain", "")).strip().lower()
            return ["subfinder", "-d", raw_target, "-silent"]

        elif tool_id == "metadata_extractor":
            raw_target = str(arguments.get("target", "")).strip()
            return ["exiftool", "-json", raw_target]

        elif tool_id == "cert_inspector":
            raw_target = str(arguments.get("target", "")).strip()
            return ["openssl", "s_client", "-connect", raw_target, "-showcerts"]

        # Default fallback to spec command name and safe allowed flags
        argv = [spec.command_name] + spec.allowed_flags
        for key, val in arguments.items():
            if val is not None and str(val).strip():
                argv.append(str(val).strip())
        return argv


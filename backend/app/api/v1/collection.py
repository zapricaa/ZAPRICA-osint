"""API endpoints for DCE (Data Collection Engine) and scoped collector jobs."""

import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_workspace, require_role
from app.models.users import User
from app.models.workspaces import Workspace
from app.models.tasks import Task
from app.models.evidence import Finding
from app.collection.coordinator import dce_coordinator
from app.collection.schemas import (
    CollectionJobRequest,
    CollectionJobResponse,
    CollectorCapabilityInfo,
)

router = APIRouter(prefix="/collection", tags=["Data Collection Engine (DCE)"])


@router.get("/collectors", response_model=List[CollectorCapabilityInfo], summary="List available DCE collectors")
async def list_collectors(
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Returns capabilities and readiness status of all approved OSINT collectors."""
    return dce_coordinator.list_capabilities()


@router.get("/collectors/{tool_id}", response_model=CollectorCapabilityInfo, summary="Get collector details")
async def get_collector_details(
    tool_id: str,
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    adapter = dce_coordinator.get_adapter(tool_id)
    if not adapter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Collector '{tool_id}' not found.")

    available, note = adapter.is_available()
    return CollectorCapabilityInfo(
        tool_id=adapter.tool_id,
        name=adapter.name,
        description=adapter.description,
        collector_type=adapter.collector_type,
        supported_target_types=list(adapter.supported_target_types),
        is_enabled=available,
        requires_approval=adapter.requires_approval,
        requires_api_key=adapter.requires_api_key,
        is_available=available,
        availability_note=note,
    )


@router.post("/jobs", response_model=CollectionJobResponse, status_code=status.HTTP_201_CREATED, summary="Submit a scoped collection job")
async def submit_collection_job(
    request: CollectionJobRequest,
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    _role=Depends(require_role(["admin", "investigator"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits and executes an authorized OSINT data collection job within an investigation scope.
    Captures raw output into immutable evidence storage and produces linked findings.
    """
    return await dce_coordinator.execute_collection(
        session=db,
        request=request,
        current_user=current_user,
        workspace=workspace,
    )


@router.get("/jobs/{task_id}", summary="Get collection job status and findings")
async def get_job_status(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the status, evidence reference, and linked findings for a collection task."""
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.workspace_id == workspace.id)
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection task not found.")

    findings = (await db.scalars(
        select(Finding).where(Finding.task_id == task_id)
    )).all()

    return {
        "task_id": str(task.id),
        "investigation_id": str(task.investigation_id),
        "tool_id": task.capability,
        "status": task.status,
        "objective": task.objective,
        "input": task.input_json,
        "findings": [
            {
                "id": str(f.id),
                "title": f.title,
                "type": f.finding_type,
                "normalized_value": f.normalized_value,
                "summary": f.summary,
                "confidence_level": f.confidence_level,
                "verification_status": f.verification_status,
            }
            for f in findings
        ],
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }


@router.delete("/jobs/{task_id}", status_code=status.HTTP_200_OK, summary="Cancel an eligible collection job")
async def cancel_job(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    _role=Depends(require_role(["admin", "investigator"])),
    db: AsyncSession = Depends(get_db),
):
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.workspace_id == workspace.id)
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection task not found.")

    if task.status in ("succeeded", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task in '{task.status}' state."
        )

    task.status = "cancelled"
    await db.commit()
    return {"message": f"Task '{task_id}' has been cancelled.", "status": "cancelled"}


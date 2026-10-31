import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_workspace, require_role
from app.models.users import User
from app.models.workspaces import Workspace
from app.models.tools import Tool, ToolVersion, AgentToolAssignment
from app.schemas.tools import (
    ToolDraftCreate,
    ToolVersionOut,
    ToolSummary,
    ToolAssignmentCreate,
    ToolAssignmentOut,
    ToolValidationOut,
)
from app.services.tool_service import ToolService

router = APIRouter(prefix="/admin/tools", tags=["Administration", "Tools"])


@router.get("", response_model=List[ToolSummary], summary="List all tools visible to administrators")
async def list_admin_tools(
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Tool)
        .where(Tool.workspace_id == workspace.id)
        .options(selectinload(Tool.versions))
    )
    tools = await db.scalars(stmt)
    results = []
    for t in tools.all():
        active_ver = t.versions[-1] if t.versions else None
        results.append(
            ToolSummary(
                id=t.id,
                tool_key=t.tool_key,
                display_name=t.display_name,
                description=t.description,
                vendor_or_source=t.vendor_or_source,
                license_id=t.license_id,
                status=t.status,
                active_version=active_ver.version if active_ver else None,
                execution_type=active_ver.execution_type if active_ver else None,
                capabilities=active_ver.capabilities if active_ver else [],
                approval_status=active_ver.approval_status if active_ver else None
            )
        )
    return results


@router.post(
    "",
    response_model=ToolVersionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a draft tool (Admin only)"
)
async def create_tool_draft(
    data: ToolDraftCreate,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    version = await ToolService.create_tool_draft(
        session=db,
        workspace_id=workspace.id,
        user_id=user.id,
        data=data,
    )
    return ToolVersionOut.model_validate(version)


@router.get(
    "/{toolId}/versions",
    response_model=List[ToolVersionOut],
    summary="List immutable versions of a tool"
)
async def list_tool_versions(
    toolId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ToolVersion).where(ToolVersion.tool_id == toolId).order_by(ToolVersion.created_at.desc())
    versions = await db.scalars(stmt)
    return [ToolVersionOut.model_validate(v) for v in versions.all()]


@router.post(
    "/{toolId}/versions/{versionId}/validate",
    response_model=ToolValidationOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run isolated validation for draft tool version"
)
async def validate_tool_version(
    toolId: uuid.UUID,
    versionId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    passed, details = await ToolService.validate_tool_version(
        session=db,
        tool_id=toolId,
        version_id=versionId,
    )
    return ToolValidationOut(
        version_id=versionId,
        approval_status="pending_review",
        tests_passed=passed,
        validation_details=details
    )


@router.post(
    "/{toolId}/versions/{versionId}/approve",
    response_model=ToolVersionOut,
    summary="Human approval of a validated tool version"
)
async def approve_tool_version(
    toolId: uuid.UUID,
    versionId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    version = await ToolService.approve_tool_version(
        session=db,
        workspace_id=workspace.id,
        user_id=user.id,
        tool_id=toolId,
        version_id=versionId,
    )
    return ToolVersionOut.model_validate(version)


@router.post(
    "/{toolId}/versions/{versionId}/publish",
    response_model=ToolVersionOut,
    summary="Publish approved tool version to eligible agents"
)
async def publish_tool_version(
    toolId: uuid.UUID,
    versionId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    version = await ToolService.publish_tool_version(
        session=db,
        tool_id=toolId,
        version_id=versionId,
    )
    return ToolVersionOut.model_validate(version)


@router.post(
    "/{toolId}/versions/{versionId}/disable",
    response_model=ToolVersionOut,
    summary="Disable a published tool version immediately"
)
async def disable_tool_version(
    toolId: uuid.UUID,
    versionId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    version = await ToolService.disable_tool_version(
        session=db,
        tool_id=toolId,
        version_id=versionId,
    )
    return ToolVersionOut.model_validate(version)

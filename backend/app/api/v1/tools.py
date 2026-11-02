from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_workspace, require_role
from app.models.users import User
from app.models.workspaces import Workspace
from app.models.policies import ToolExecutionPolicy, WebsiteAutomationPolicy
from app.schemas.tools import ToolSummary
from app.services.tool_service import ToolService

router = APIRouter(prefix="/tools", tags=["Tools & Execution Policies"])


class ToolExecutionPolicySchema(BaseModel):
    tool_key: str
    execution_mode: str = "AUTOMATED_ALLOWED"  # AUTOMATED_ALLOWED, HUMAN_ASSISTED_ONLY, API_ONLY, BLOCKED
    browser_automation: bool = False
    terminal_sandboxed: bool = True
    requires_admin_approval: bool = False


class UpdateToolExecutionPolicyRequest(BaseModel):
    execution_mode: str = Field(..., pattern="^(AUTOMATED_ALLOWED|HUMAN_ASSISTED_ONLY|API_ONLY|BLOCKED)$")
    browser_automation: bool = False
    terminal_sandboxed: bool = True
    requires_admin_approval: bool = False


@router.get("", response_model=List[ToolSummary], summary="List approved tools available to agents")
async def list_available_tools(
    capability: Optional[str] = Query(None),
    execution_type: Optional[str] = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AC-TIMS-05: Returns only approved/published tool versions."""
    versions = await ToolService.list_available_tools(
        session=db,
        workspace_id=workspace.id,
        capability=capability,
        execution_type=execution_type,
    )
    summaries = []
    for v in versions:
        summaries.append(
            ToolSummary(
                id=v.id,
                tool_key=v.manifest_json.get("tool_key", "unknown"),
                display_name=v.manifest_json.get("tool_key", "Tool").replace("_", " ").title(),
                description=v.playbook_markdown[:150],
                vendor_or_source="Verified Registry",
                license_id="MIT",
                status="published",
                active_version=v.version,
                execution_type=v.execution_type,
                capabilities=v.capabilities,
                approval_status=v.approval_status
            )
        )
    return summaries


@router.get("/{tool_id}/execution-policy", response_model=ToolExecutionPolicySchema)
async def get_tool_execution_policy(
    tool_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the execution policy and automation constraints for a tool."""
    tool_key = tool_id.lower().strip()

    # Special handling for Epieos requirement (Section 2.6 & Section 5)
    if tool_key == "epieos":
        return ToolExecutionPolicySchema(
            tool_key="epieos",
            execution_mode="HUMAN_ASSISTED_ONLY",
            browser_automation=False,
            terminal_sandboxed=False,
            requires_admin_approval=False,
        )

    policy = await db.scalar(select(ToolExecutionPolicy).where(ToolExecutionPolicy.tool_key == tool_key))
    if not policy:
        # Default policy
        return ToolExecutionPolicySchema(
            tool_key=tool_key,
            execution_mode="AUTOMATED_ALLOWED",
            browser_automation=True if "browser" in tool_key else False,
            terminal_sandboxed=True,
            requires_admin_approval=False,
        )

    return ToolExecutionPolicySchema(
        tool_key=policy.tool_key,
        execution_mode=policy.execution_mode,
        browser_automation=policy.browser_automation,
        terminal_sandboxed=policy.terminal_sandboxed,
        requires_admin_approval=policy.requires_admin_approval,
    )


@router.put("/{tool_id}/execution-policy", response_model=ToolExecutionPolicySchema)
async def update_tool_execution_policy(
    tool_id: str,
    payload: UpdateToolExecutionPolicyRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Updates the execution policy and automation rules for a tool (Administrator only)."""
    tool_key = tool_id.lower().strip()

    # Epieos policy constraint: cannot be overridden to automated without official written API approval
    if tool_key == "epieos" and payload.execution_mode != "HUMAN_ASSISTED_ONLY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy Invariant: Epieos is strictly restricted to HUMAN_ASSISTED_ONLY unless an authorized official API adapter is configured."
        )

    policy = await db.scalar(select(ToolExecutionPolicy).where(ToolExecutionPolicy.tool_key == tool_key))
    if not policy:
        policy = ToolExecutionPolicy(
            tool_key=tool_key,
            execution_mode=payload.execution_mode,
            browser_automation=payload.browser_automation,
            terminal_sandboxed=payload.terminal_sandboxed,
            requires_admin_approval=payload.requires_admin_approval,
        )
        db.add(policy)
    else:
        policy.execution_mode = payload.execution_mode
        policy.browser_automation = payload.browser_automation
        policy.terminal_sandboxed = payload.terminal_sandboxed
        policy.requires_admin_approval = payload.requires_admin_approval

    await db.commit()
    await db.refresh(policy)

    return ToolExecutionPolicySchema(
        tool_key=policy.tool_key,
        execution_mode=policy.execution_mode,
        browser_automation=policy.browser_automation,
        terminal_sandboxed=policy.terminal_sandboxed,
        requires_admin_approval=policy.requires_admin_approval,
    )

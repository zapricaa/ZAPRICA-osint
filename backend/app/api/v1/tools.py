from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_workspace
from app.models.users import User
from app.models.workspaces import Workspace
from app.schemas.tools import ToolSummary
from app.services.tool_service import ToolService

router = APIRouter(prefix="/tools", tags=["Tools"])


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

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.events import event_bus
from app.api.deps import get_current_user, get_current_workspace, require_role
from app.models.users import User
from app.models.workspaces import Workspace
from app.schemas.investigations import (
    InvestigationCreate,
    InvestigationOut,
    InvestigationListOut,
    InvestigationActionResponse,
)
from app.schemas.entities import (
    TaskOut,
    FindingOut,
    FindingListOut,
    EvidenceArtifactOut,
    ReportOut,
)
from app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/investigations", tags=["Investigations"])


@router.get("", response_model=InvestigationListOut, summary="List investigations in workspace")
async def list_investigations(
    status: Optional[str] = Query(None, description="Filter by investigation status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await InvestigationService.list_investigations(
        session=db,
        workspace_id=workspace.id,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
    return InvestigationListOut(
        items=[InvestigationOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=InvestigationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an investigation and explicit scope"
)
async def create_investigation(
    data: InvestigationCreate,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin", "investigator"])),
    db: AsyncSession = Depends(get_db),
):
    inv = await InvestigationService.create_investigation(
        session=db,
        workspace_id=workspace.id,
        user_id=user.id,
        data=data,
    )
    return InvestigationOut.model_validate(inv)


@router.get("/{investigationId}", response_model=InvestigationOut, summary="Get investigation details")
async def get_investigation(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await InvestigationService.get_investigation(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return InvestigationOut.model_validate(inv)


@router.post(
    "/{investigationId}/start",
    response_model=InvestigationActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Validate and start an investigation"
)
async def start_investigation(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin", "investigator"])),
    db: AsyncSession = Depends(get_db),
):
    inv = await InvestigationService.start_investigation(
        session=db,
        workspace_id=workspace.id,
        user_id=user.id,
        investigation_id=investigationId,
    )
    return InvestigationActionResponse(
        id=inv.id,
        status=inv.status,
        message="Investigation validated and queued for agent execution."
    )


@router.post(
    "/{investigationId}/pause",
    response_model=InvestigationActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pause an investigation"
)
async def pause_investigation(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin", "investigator"])),
    db: AsyncSession = Depends(get_db),
):
    inv = await InvestigationService.pause_investigation(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return InvestigationActionResponse(
        id=inv.id,
        status=inv.status,
        message="Investigation pause requested."
    )


@router.post(
    "/{investigationId}/resume",
    response_model=InvestigationActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resume a paused investigation"
)
async def resume_investigation(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin", "investigator"])),
    db: AsyncSession = Depends(get_db),
):
    inv = await InvestigationService.resume_investigation(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return InvestigationActionResponse(
        id=inv.id,
        status=inv.status,
        message="Investigation resumed after policy revalidation."
    )


@router.post(
    "/{investigationId}/cancel",
    response_model=InvestigationActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cancel an investigation"
)
async def cancel_investigation(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin", "investigator"])),
    db: AsyncSession = Depends(get_db),
):
    inv = await InvestigationService.cancel_investigation(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return InvestigationActionResponse(
        id=inv.id,
        status=inv.status,
        message="Investigation cancelled and worker shutdown initiated."
    )


@router.get(
    "/{investigationId}/tasks",
    response_model=List[TaskOut],
    summary="List tasks for an investigation"
)
async def list_tasks(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tasks = await InvestigationService.list_tasks(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return [TaskOut.model_validate(t) for t in tasks]


@router.get(
    "/{investigationId}/findings",
    response_model=FindingListOut,
    summary="List processed findings with provenance references"
)
async def list_findings(
    investigationId: uuid.UUID,
    verification_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    findings, total = await InvestigationService.list_findings(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
        verification_status=verification_status,
        page=page,
        page_size=page_size,
    )
    return FindingListOut(
        items=[FindingOut.model_validate(f) for f in findings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{investigationId}/evidence",
    response_model=List[EvidenceArtifactOut],
    summary="List evidence artifacts metadata"
)
async def list_evidence(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    artifacts = await InvestigationService.list_evidence(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return [EvidenceArtifactOut.model_validate(a) for a in artifacts]


@router.get(
    "/{investigationId}/reports",
    response_model=List[ReportOut],
    summary="List reports for an investigation"
)
async def list_reports(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reports = await InvestigationService.list_reports(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return [ReportOut.model_validate(r) for r in reports]


@router.post(
    "/{investigationId}/reports",
    response_model=ReportOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate report from current verified findings"
)
async def generate_report(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    _role=Depends(require_role(["admin", "investigator", "reviewer"])),
    db: AsyncSession = Depends(get_db),
):
    from app.services.report_service import ReportService
    report = await ReportService.generate_investigation_report(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return ReportOut.model_validate(report)


@router.get(
    "/{investigationId}/reports/export/json",
    summary="Export latest report as JSON (AC-REPORT-04)"
)
async def export_report_json(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.report_service import ReportService
    content = await ReportService.export_json(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=report_{investigationId}.json"}
    )


@router.get(
    "/{investigationId}/reports/export/csv",
    summary="Export findings as CSV (AC-REPORT-04)"
)
async def export_report_csv(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.report_service import ReportService
    content = await ReportService.export_csv(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=findings_{investigationId}.csv"}
    )


@router.get(
    "/{investigationId}/events",
    summary="Stream investigation status events using Server-Sent Events"
)
async def stream_events(
    investigationId: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify access to investigation
    await InvestigationService.get_investigation(
        session=db,
        workspace_id=workspace.id,
        investigation_id=investigationId,
    )

    return StreamingResponse(
        event_bus.subscribe(str(investigationId)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

"""Administrator Dashboard API: User Management, Invitations, Roles, Sessions, and Audit."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_system_role
from app.core.database import get_db
from app.models.invitations import Invitation
from app.models.rbac import Role, UserRole, UserToolPermission
from app.models.reports import AuditEvent
from app.models.sessions import LoginAttempt, Session
from app.models.tools import Tool
from app.models.users import User
from app.core.safe_mode import safe_mode_controller
from app.schemas.auth import (
    AdminUserCreateRequest,
    AdminUserRoleUpdateRequest,
    AdminUserStatusUpdateRequest,
    InvitationCreateRequest,
    InvitationOut,
    LoginAttemptOut,
    SessionOut,
    UserDetailOut,
    UserToolPermissionAssignRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/admin", tags=["Administrator Dashboard"])


# -----------------------------------------------------------------------------
# User Management
# -----------------------------------------------------------------------------

@router.get(
    "/users",
    response_model=List[UserDetailOut],
    summary="List all platform users with roles and status",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def list_users(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List users with active status, assigned system roles, and MFA enrollment."""
    stmt = (
        select(User)
        .options(
            selectinload(User.user_roles).selectinload(UserRole.role),
        )
        .order_by(desc(User.created_at))
        .offset(offset)
        .limit(limit)
    )
    if status_filter:
        stmt = stmt.where(User.status == status_filter)

    users = (await db.scalars(stmt)).all()

    return [
        UserDetailOut(
            id=u.id,
            username=u.username,
            email=u.email,
            display_name=u.display_name,
            status=u.status,
            roles=[ur.role.name for ur in u.user_roles if ur.role],
            permissions=[],
            mfa_enabled=u.mfa_enabled,
            failed_login_count=u.failed_login_count,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]


@router.post(
    "/users",
    response_model=UserDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Provision user directly by administrator",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def create_user(
    payload: AdminUserCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Provision a user directly, assign password, role, and workspace."""
    ip_addr = request.client.host if request.client else None
    new_user, assigned_role = await AuthService.create_user_by_admin(
        session=db, data=payload, creator=current_user, ip_address=ip_addr
    )

    return UserDetailOut(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        display_name=new_user.display_name,
        status=new_user.status,
        roles=[assigned_role],
        permissions=[],
        mfa_enabled=False,
        failed_login_count=0,
        created_at=new_user.created_at,
        last_login_at=None,
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=UserDetailOut,
    summary="Update user status: active, suspended, disabled, or revoked",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def update_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change account status. Suspended, disabled, or revoked users immediately lose all active sessions."""
    ip_addr = request.client.host if request.client else None
    updated = await AuthService.update_user_status(
        session=db,
        target_user_id=user_id,
        new_status=payload.status,
        admin=current_user,
        reason=payload.reason,
        ip_address=ip_addr,
    )

    roles = await AuthService.get_user_roles(db, updated.id)
    return UserDetailOut(
        id=updated.id,
        username=updated.username,
        email=updated.email,
        display_name=updated.display_name,
        status=updated.status,
        roles=roles,
        permissions=[],
        mfa_enabled=updated.mfa_enabled,
        failed_login_count=updated.failed_login_count,
        created_at=updated.created_at,
        last_login_at=updated.last_login_at,
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=UserDetailOut,
    summary="Update user platform role",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN"]))],
)
async def update_user_role(
    user_id: uuid.UUID,
    payload: AdminUserRoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign or modify system role (SUPER_ADMIN, ADMINISTRATOR, INVESTIGATOR, ANALYST)."""
    roles = await AuthService.ensure_default_roles(db)
    target_role = roles.get(payload.role)
    if not target_role:
        raise HTTPException(status_code=400, detail=f"Invalid role '{payload.role}'.")

    # Clear old roles and set new
    existing_roles = (
        await db.scalars(select(UserRole).where(UserRole.user_id == user_id))
    ).all()
    for er in existing_roles:
        await db.delete(er)

    new_role_link = UserRole(
        user_id=user_id,
        role_id=target_role.id,
        granted_by=current_user.id,
    )
    db.add(new_role_link)
    await db.commit()

    target_user = await db.scalar(select(User).where(User.id == user_id))
    return UserDetailOut(
        id=target_user.id,
        username=target_user.username,
        email=target_user.email,
        display_name=target_user.display_name,
        status=target_user.status,
        roles=[payload.role],
        permissions=[],
        mfa_enabled=target_user.mfa_enabled,
        failed_login_count=target_user.failed_login_count,
        created_at=target_user.created_at,
        last_login_at=target_user.last_login_at,
    )


# -----------------------------------------------------------------------------
# Invitations Management
# -----------------------------------------------------------------------------

@router.post(
    "/invitations",
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a secure single-use invitation",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def create_invitation(
    payload: InvitationCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a single-use onboarding invitation link with cryptographic token."""
    ip_addr = request.client.host if request.client else None
    return await AuthService.create_invitation(
        session=db, data=payload, creator=current_user, ip_address=ip_addr
    )


@router.get(
    "/invitations",
    response_model=List[InvitationOut],
    summary="List all pending and redeemed invitations",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def list_invitations(
    db: AsyncSession = Depends(get_db),
):
    """List invitation links and their redemption status."""
    stmt = (
        select(Invitation)
        .options(selectinload(Invitation.role))
        .order_by(desc(Invitation.created_at))
    )
    invitations = (await db.scalars(stmt)).all()
    return [
        InvitationOut(
            id=inv.id,
            email=inv.email,
            role=inv.role.name if inv.role else "INVESTIGATOR",
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invitations
    ]


@router.delete(
    "/invitations/{invitation_id}",
    summary="Revoke pending invitation",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Revoke an active invitation so it can no longer be redeemed."""
    inv = await db.scalar(select(Invitation).where(Invitation.id == invitation_id))
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    inv.status = "revoked"
    await db.commit()
    return {"message": "Invitation revoked successfully."}


# -----------------------------------------------------------------------------
# Active Sessions & Monitoring
# -----------------------------------------------------------------------------

@router.get(
    "/sessions",
    response_model=List[SessionOut],
    summary="List active platform sessions",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def list_sessions(
    user_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List sessions and their activity status."""
    stmt = (
        select(Session)
        .order_by(desc(Session.created_at))
        .limit(100)
    )
    if user_id:
        stmt = stmt.where(Session.user_id == user_id)

    sessions = (await db.scalars(stmt)).all()
    return [
        SessionOut(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_active=s.is_active,
        )
        for s in sessions
    ]


@router.delete(
    "/sessions/{session_id}",
    summary="Force-revoke active user session",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def revoke_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Terminate and invalidate a session immediately."""
    sess = await db.scalar(select(Session).where(Session.id == session_id))
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    sess.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Session terminated successfully."}


# -----------------------------------------------------------------------------
# Login Activity & Security Audit Logs
# -----------------------------------------------------------------------------

@router.get(
    "/login-attempts",
    response_model=List[LoginAttemptOut],
    summary="View login activity and failed attempt audit trail",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def list_login_attempts(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Inspect login audit history for brute-force monitoring."""
    stmt = select(LoginAttempt).order_by(desc(LoginAttempt.attempted_at)).limit(limit)
    attempts = (await db.scalars(stmt)).all()
    return [
        LoginAttemptOut(
            id=a.id,
            username_or_email=a.username_or_email,
            ip_address=a.ip_address,
            user_agent=a.user_agent,
            successful=a.successful,
            failure_reason=a.failure_reason,
            attempted_at=a.attempted_at,
        )
        for a in attempts
    ]


@router.get(
    "/audit-logs",
    summary="View security audit log events",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def list_audit_events(
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Inspect security audit trail."""
    stmt = select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    events = (await db.scalars(stmt)).all()
    return [
        {
            "id": str(e.id),
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "actor_type": e.actor_type,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": str(e.resource_id) if e.resource_id else None,
            "details": e.metadata_redacted,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


# -----------------------------------------------------------------------------
# Tool Permissions Management
# -----------------------------------------------------------------------------

@router.post(
    "/tools/{tool_id}/permissions",
    summary="Grant tool permission to a user",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN"]))],
)
async def grant_tool_permission(
    tool_id: uuid.UUID,
    payload: UserToolPermissionAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grant specific tool execution permission to a user."""
    tool = await db.scalar(select(Tool).where(Tool.id == tool_id))
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found.")

    target_user = await db.scalar(select(User).where(User.id == payload.user_id))
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    existing = await db.scalar(
        select(UserToolPermission).where(
            and_(
                UserToolPermission.user_id == payload.user_id,
                UserToolPermission.tool_id == tool_id,
            )
        )
    )
    if existing:
        existing.revoked_at = None
    else:
        db.add(
            UserToolPermission(
                user_id=payload.user_id,
                tool_id=tool_id,
                granted_by=current_user.id,
            )
        )

    await db.commit()
    return {"message": f"Permission for tool '{tool.name}' granted to user '{target_user.username}'."}


# -----------------------------------------------------------------------------
# Safe Startup Mode Management
# -----------------------------------------------------------------------------

@router.get(
    "/safe-mode",
    summary="Get Safe Startup Mode status and agent states",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN", "ADMINISTRATOR"]))],
)
async def get_safe_mode_status():
    """Returns safe startup flags, agent idle states, and execution policies."""
    return safe_mode_controller.get_status()


@router.post(
    "/safe-mode/terminal-execution",
    summary="Administrator toggle for terminal execution capability",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN"]))],
)
async def toggle_terminal_execution(
    enabled: bool = Query(...),
    reason: str = Query("Admin activation of approved CLI adapters", min_length=5),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly enable or disable terminal execution capabilities."""
    if enabled:
        safe_mode_controller.enable_terminal_execution(current_user.username, reason)
    else:
        safe_mode_controller.disable_terminal_execution(current_user.username)

    # Log security audit event
    user_mem = await db.scalar(
        select(WorkspaceMembership).where(
            and_(WorkspaceMembership.user_id == current_user.id, WorkspaceMembership.status == "active")
        )
    )
    ws_id = user_mem.workspace_id if user_mem else uuid.uuid4()

    db.add(
        AuditEvent(
            workspace_id=ws_id,
            actor_id=str(current_user.id),
            actor_type="user",
            action="terminal_execution_toggled",
            resource_type="system",
            metadata_redacted={"enabled": enabled, "reason": reason},
        )
    )
    await db.commit()

    return {
        "terminal_execution_enabled": safe_mode_controller.is_terminal_execution_enabled,
        "message": f"Terminal execution has been {'enabled' if enabled else 'disabled'}.",
    }


@router.post(
    "/safe-mode/toggle",
    summary="Toggle safe mode globally",
    dependencies=[Depends(require_system_role(["SUPER_ADMIN"]))],
)
async def toggle_safe_mode(
    enabled: bool = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle safe mode globally."""
    safe_mode_controller.set_safe_mode(enabled, current_user.username)
    user_mem = await db.scalar(
        select(WorkspaceMembership).where(
            and_(WorkspaceMembership.user_id == current_user.id, WorkspaceMembership.status == "active")
        )
    )
    ws_id = user_mem.workspace_id if user_mem else uuid.uuid4()

    db.add(
        AuditEvent(
            workspace_id=ws_id,
            actor_id=str(current_user.id),
            actor_type="user",
            action="safe_mode_toggled",
            resource_type="system",
            metadata_redacted={"enabled": enabled},
        )
    )
    await db.commit()
    return safe_mode_controller.get_status()


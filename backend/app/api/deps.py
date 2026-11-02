"""Authentication and Authorization Dependencies for Invite-Only Platform."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token, hash_session_token
from app.models.rbac import Role, UserRole
from app.models.sessions import Session
from app.models.users import User
from app.models.workspaces import Workspace, WorkspaceMembership

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    session_token: Optional[str] = Cookie(None, alias="session_token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate user via:
    1. Secure HttpOnly session cookie ('session_token'), OR
    2. Bearer JWT Authorization header.
    Verifies user status is active and account is not suspended or locked.
    """
    user_id: Optional[uuid.UUID] = None

    # 1. Check Bearer Authorization Header first (explicit client header takes precedence)
    if credentials and credentials.credentials:
        token_str = credentials.credentials
        # Check if the bearer token is a raw session token or a JWT
        if len(token_str) > 60 and "." not in token_str:
            # Raw session token in header
            token_hash = hash_session_token(token_str)
            db_session = await db.scalar(
                select(Session)
                .where(Session.session_token_hash == token_hash)
                .options(
                    selectinload(Session.user)
                    .selectinload(User.user_roles)
                    .selectinload(UserRole.role),
                    selectinload(Session.user)
                    .selectinload(User.memberships)
                    .selectinload(WorkspaceMembership.workspace),
                )
            )
            if db_session and db_session.is_active:
                user = db_session.user
                if user.status != "active":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Account is {user.status}.",
                    )
                return user

        # JWT Bearer Token
        payload = decode_access_token(token_str)
        if payload and "sub" in payload:
            try:
                user_id = uuid.UUID(payload["sub"])
            except (ValueError, TypeError):
                pass

    # 2. Check HttpOnly Session Cookie if no Bearer credentials provided
    elif session_token:
        token_hash = hash_session_token(session_token)
        sess_stmt = (
            select(Session)
            .where(Session.session_token_hash == token_hash)
            .options(
                selectinload(Session.user)
                .selectinload(User.user_roles)
                .selectinload(UserRole.role),
                selectinload(Session.user)
                .selectinload(User.memberships)
                .selectinload(WorkspaceMembership.workspace),
            )
        )
        db_session = await db.scalar(sess_stmt)
        if db_session and db_session.is_active:
            db_session.last_active_at = datetime.now(timezone.utc)
            await db.commit()
            user = db_session.user
            if user.status != "active":
                # Immediately revoke session
                db_session.revoked_at = datetime.now(timezone.utc)
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account is {user.status}. Contact your administrator.",
                )
            if user.is_locked:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is temporarily locked due to excessive failed attempts.",
                )
            return user

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with valid credentials.",
        )

    # Fetch User
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.user_roles).selectinload(UserRole.role),
            selectinload(User.memberships).selectinload(WorkspaceMembership.workspace),
        )
    )
    user = await db.scalar(stmt)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Contact your administrator.",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to excessive failed attempts.",
        )

    return user


async def get_current_workspace(
    user: User = Depends(get_current_user),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """Validate that the user is an authorized member of the requested workspace."""
    target_ws_id: Optional[uuid.UUID] = None

    if x_workspace_id:
        try:
            target_ws_id = uuid.UUID(x_workspace_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Workspace-ID header format. Must be a valid UUID.",
            )
    else:
        active_memberships = [
            m for m in user.memberships
            if m.status == "active" and m.workspace.status == "active"
        ]
        if not active_memberships:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to any active workspace.",
            )
        target_ws_id = active_memberships[0].workspace_id

    matching_membership = next(
        (m for m in user.memberships if m.workspace_id == target_ws_id and m.status == "active"),
        None,
    )
    if not matching_membership:
        # Check if user has global SUPER_ADMIN role
        user_roles = [ur.role.name for ur in user.user_roles if ur.role]
        if "SUPER_ADMIN" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: User is not an authorized member of the specified workspace.",
            )

    workspace = await db.scalar(select(Workspace).where(Workspace.id == target_ws_id))
    if not workspace or workspace.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or disabled.",
        )

    return workspace


def _normalize_role_str(role: str) -> str:
    r = role.strip().lower()
    if r in ("admin", "administrator"):
        return "admin"
    if r in ("super_admin", "superadmin", "super-admin"):
        return "super_admin"
    return r


def _roles_match(user_role: Optional[str], allowed_roles: List[str]) -> bool:
    if not user_role:
        return False
    norm_user = _normalize_role_str(user_role)
    norm_allowed = {_normalize_role_str(r) for r in allowed_roles}
    return norm_user in norm_allowed


def require_role(allowed_roles: List[str]):
    """Enforce workspace role permission check."""
    async def role_checker(
        user: User = Depends(get_current_user),
        workspace: Workspace = Depends(get_current_workspace),
    ) -> WorkspaceMembership:
        user_roles = [ur.role.name for ur in user.user_roles if ur.role]
        if "SUPER_ADMIN" in user_roles or any(_normalize_role_str(r) == "super_admin" for r in user_roles):
            # Super Admin bypasses workspace role constraints
            matching = next(
                (m for m in user.memberships if m.workspace_id == workspace.id),
                None,
            )
            if matching:
                return matching
            # Synthesize virtual membership for Super Admin
            return WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role="super_admin",
                status="active",
            )

        membership = next(
            (m for m in user.memberships if m.workspace_id == workspace.id and m.status == "active"),
            None,
        )
        if not membership or not _roles_match(membership.role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {allowed_roles}. Current role: {getattr(membership, 'role', 'none')}.",
            )
        return membership

    return role_checker


def require_system_role(allowed_roles: List[str]):
    """Enforce platform-level system role check (SUPER_ADMIN, ADMINISTRATOR, etc.)."""
    async def system_role_checker(
        user: User = Depends(get_current_user),
    ) -> User:
        user_roles = [ur.role.name for ur in user.user_roles if ur.role]
        if "SUPER_ADMIN" in user_roles or any(_normalize_role_str(r) == "super_admin" for r in user_roles):
            return user

        norm_allowed = {_normalize_role_str(r) for r in allowed_roles}
        if not any(_normalize_role_str(r) in norm_allowed for r in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Administrative access denied. Requires system role in {allowed_roles}.",
            )
        return user

    return system_role_checker

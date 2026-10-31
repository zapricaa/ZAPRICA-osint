import uuid
from typing import List, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.users import User
from app.models.workspaces import Workspace, WorkspaceMembership

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Validate Bearer JWT and return authenticated User."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credential required."
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed authentication token."
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user subject in token."
        )

    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.memberships).selectinload(WorkspaceMembership.workspace)
        )
    )
    user = await db.scalar(stmt)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists."
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated or suspended."
        )

    return user


async def get_current_workspace(
    user: User = Depends(get_current_user),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db)
) -> Workspace:
    """Validate that the user is an authorized member of the requested workspace."""
    target_ws_id: Optional[uuid.UUID] = None

    if x_workspace_id:
        try:
            target_ws_id = uuid.UUID(x_workspace_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Workspace-ID header format. Must be a valid UUID."
            )
    else:
        # Default to first active membership if header is not passed
        active_memberships = [
            m for m in user.memberships
            if m.status == "active" and m.workspace.status == "active"
        ]
        if not active_memberships:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to any active workspace."
            )
        target_ws_id = active_memberships[0].workspace_id

    # Check that user actually has membership in target_ws_id
    matching_membership = next(
        (m for m in user.memberships if m.workspace_id == target_ws_id and m.status == "active"),
        None
    )
    if not matching_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: User is not an authorized member of the specified workspace."
        )

    workspace = await db.scalar(select(Workspace).where(Workspace.id == target_ws_id))
    if not workspace or workspace.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or disabled."
        )

    return workspace


def require_role(allowed_roles: List[str]):
    """Enforce workspace role permission check."""
    async def role_checker(
        user: User = Depends(get_current_user),
        workspace: Workspace = Depends(get_current_workspace)
    ) -> WorkspaceMembership:
        membership = next(
            (m for m in user.memberships if m.workspace_id == workspace.id and m.status == "active"),
            None
        )
        if not membership or membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {allowed_roles}. Current role: {getattr(membership, 'role', 'none')}."
            )
        return membership

    return role_checker

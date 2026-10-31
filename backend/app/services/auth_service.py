import re
import uuid
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models.users import User
from app.models.workspaces import Workspace, WorkspaceMembership
from app.schemas.auth import UserCreate, UserLogin, TokenResponse, CurrentUserOut, WorkspaceMembershipOut


class AuthService:
    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug or "workspace"

    @classmethod
    async def register_user(
        cls, session: AsyncSession, data: UserCreate
    ) -> Tuple[User, Workspace, WorkspaceMembership]:
        # Check if email already registered
        normalized_email = data.email.lower().strip()
        existing = await session.scalar(select(User).where(User.email == normalized_email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists."
            )

        # Create user
        user = User(
            email=normalized_email,
            display_name=data.display_name.strip(),
            password_hash=hash_password(data.password),
            status="active"
        )
        session.add(user)
        await session.flush()

        # Create user's initial workspace
        ws_name = data.workspace_name or f"{data.display_name.strip()}'s Workspace"
        base_slug = cls._slugify(ws_name)
        slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"

        workspace = Workspace(
            name=ws_name,
            slug=slug,
            status="active"
        )
        session.add(workspace)
        await session.flush()

        # Create workspace membership as admin
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=user.id,
            role="admin",
            status="active"
        )
        session.add(membership)
        await session.commit()

        return user, workspace, membership

    @classmethod
    async def authenticate_user(
        cls, session: AsyncSession, data: UserLogin
    ) -> TokenResponse:
        normalized_email = data.email.lower().strip()
        stmt = (
            select(User)
            .where(User.email == normalized_email)
            .options(
                selectinload(User.memberships).selectinload(WorkspaceMembership.workspace)
            )
        )
        user = await session.scalar(stmt)
        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive or disabled."
            )

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        # Build membership info
        memberships_out = []
        active_ws_id = None
        role = "investigator"

        for m in user.memberships:
            if m.status == "active" and m.workspace.status == "active":
                memberships_out.append(
                    WorkspaceMembershipOut(
                        workspace_id=m.workspace_id,
                        workspace_name=m.workspace.name,
                        workspace_slug=m.workspace.slug,
                        role=m.role,
                        status=m.status
                    )
                )
                if not active_ws_id:
                    active_ws_id = m.workspace_id
                    role = m.role

        user_out = CurrentUserOut(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            memberships=memberships_out
        )

        token = create_access_token(
            subject=str(user.id),
            workspace_id=str(active_ws_id) if active_ws_id else None,
            role=role
        )

        return TokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_out,
            active_workspace_id=active_ws_id
        )

    @classmethod
    async def get_current_user_profile(
        cls, session: AsyncSession, user_id: uuid.UUID
    ) -> CurrentUserOut:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.memberships).selectinload(WorkspaceMembership.workspace)
            )
        )
        user = await session.scalar(stmt)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        memberships_out = [
            WorkspaceMembershipOut(
                workspace_id=m.workspace_id,
                workspace_name=m.workspace.name,
                workspace_slug=m.workspace.slug,
                role=m.role,
                status=m.status
            )
            for m in user.memberships
            if m.status == "active" and m.workspace.status == "active"
        ]

        return CurrentUserOut(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            memberships=memberships_out
        )

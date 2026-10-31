"""Authentication, Session Management, RBAC, and Invite-Only Service."""

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_invitation_token,
    generate_mfa_secret,
    generate_session_token,
    get_mfa_uri,
    hash_invitation_token,
    hash_password,
    hash_session_token,
    verify_mfa_code,
    verify_password,
)
from app.models.invitations import Invitation
from app.models.rbac import Permission, Role, RolePermission, UserRole, UserToolPermission
from app.models.reports import AuditEvent
from app.models.sessions import LoginAttempt, Session
from app.models.tools import Tool
from app.models.users import User
from app.models.workspaces import Workspace, WorkspaceMembership
from app.schemas.auth import (
    AdminUserCreateRequest,
    BootstrapAdminRequest,
    CurrentUserOut,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationOut,
    MFARequiredResponse,
    MFASetupResponse,
    TokenResponse,
    WorkspaceMembershipOut,
)


class AuthService:
    """Manages secure invite-only registration, authentication, sessions, and RBAC."""

    DEFAULT_ROLES = ["SUPER_ADMIN", "ADMINISTRATOR", "INVESTIGATOR", "ANALYST"]

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug or "workspace"

    @classmethod
    async def ensure_default_roles(cls, session: AsyncSession) -> Dict[str, Role]:
        """Ensure standard system roles exist in the database."""
        roles: Dict[str, Role] = {}
        for role_name in cls.DEFAULT_ROLES:
            stmt = select(Role).where(Role.name == role_name)
            existing = await session.scalar(stmt)
            if not existing:
                desc = {
                    "SUPER_ADMIN": "Complete platform administration, user management, and security controls.",
                    "ADMINISTRATOR": "Investigation management, assigned users, and tool configuration.",
                    "INVESTIGATOR": "Create investigations, execute authorized tools, and inspect findings.",
                    "ANALYST": "Read-only evidence inspection and intelligence report export.",
                }.get(role_name, f"{role_name} role")

                role = Role(name=role_name, description=desc, is_system=True)
                session.add(role)
                await session.flush()
                roles[role_name] = role
            else:
                roles[role_name] = existing

        await session.commit()
        return roles

    @classmethod
    async def bootstrap_super_admin(
        cls, session: AsyncSession, data: BootstrapAdminRequest, ip_address: Optional[str] = None
    ) -> Tuple[User, Workspace, str]:
        """
        One-time bootstrap process for the first SUPER_ADMIN account.
        Fails if any user already exists in the system.
        """
        user_count = await session.scalar(select(func.count(User.id)))
        if user_count and user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Violation: System has already been bootstrapped. Use administrator login.",
            )

        roles = await cls.ensure_default_roles(session)
        super_admin_role = roles["SUPER_ADMIN"]

        # Create Super Admin User
        admin_user = User(
            username=data.username.lower().strip(),
            email=data.email.lower().strip(),
            display_name=data.display_name.strip(),
            password_hash=hash_password(data.password),
            status="active",
        )
        session.add(admin_user)
        await session.flush()

        # Assign SUPER_ADMIN role
        user_role = UserRole(
            user_id=admin_user.id,
            role_id=super_admin_role.id,
            granted_by=admin_user.id,
        )
        session.add(user_role)

        # Create Primary Workspace
        ws_name = data.workspace_name or "Primary Workspace"
        workspace = Workspace(
            name=ws_name,
            slug=f"{cls._slugify(ws_name)}-{str(uuid.uuid4())[:8]}",
            status="active",
        )
        session.add(workspace)
        await session.flush()

        # Workspace membership
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=admin_user.id,
            role="super_admin",
            status="active",
        )
        session.add(membership)

        # Audit Event
        audit = AuditEvent(
            workspace_id=workspace.id,
            actor_id=admin_user.id,
            actor_type="user",
            event_type="system_bootstrap",
            target_type="user",
            target_id=str(admin_user.id),
            ip_address=ip_address,
            details_json={"username": admin_user.username, "role": "SUPER_ADMIN"},
        )
        session.add(audit)
        await session.commit()

        # Generate initial session token
        session_token = generate_session_token()
        sess = Session(
            user_id=admin_user.id,
            session_token_hash=hash_session_token(session_token),
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(sess)
        await session.commit()

        return admin_user, workspace, session_token

    @classmethod
    async def create_user_by_admin(
        cls,
        session: AsyncSession,
        data: AdminUserCreateRequest,
        creator: User,
        ip_address: Optional[str] = None,
    ) -> Tuple[User, str]:
        """Direct user provisioning by an authorized administrator."""
        # Check permissions
        caller_roles = await cls.get_user_roles(session, creator.id)
        if "SUPER_ADMIN" not in caller_roles and "ADMINISTRATOR" not in caller_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission Denied: Only administrators can create users.",
            )

        # Check unique username and email
        normalized_email = data.email.lower().strip()
        normalized_username = data.username.lower().strip()

        conflict = await session.scalar(
            select(User).where(or_(User.email == normalized_email, User.username == normalized_username))
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this username or email already exists.",
            )

        roles = await cls.ensure_default_roles(session)
        target_role = roles.get(data.role)
        if not target_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{data.role}'.",
            )

        new_user = User(
            username=normalized_username,
            email=normalized_email,
            display_name=data.display_name.strip(),
            password_hash=hash_password(data.password),
            status="active",
        )
        session.add(new_user)
        await session.flush()

        # Assign Role
        u_role = UserRole(
            user_id=new_user.id,
            role_id=target_role.id,
            granted_by=creator.id,
        )
        session.add(u_role)

        # Workspace assignment
        ws_id = data.workspace_id
        if not ws_id:
            # Assign to creator's active workspace or first available
            membership_stmt = select(WorkspaceMembership).where(
                and_(WorkspaceMembership.user_id == creator.id, WorkspaceMembership.status == "active")
            )
            creator_mem = await session.scalar(membership_stmt)
            ws_id = creator_mem.workspace_id if creator_mem else None

        if ws_id:
            membership = WorkspaceMembership(
                workspace_id=ws_id,
                user_id=new_user.id,
                role=data.role.lower(),
                status="active",
            )
            session.add(membership)

        # Audit Event
        session.add(
            AuditEvent(
                workspace_id=ws_id,
                actor_id=creator.id,
                actor_type="user",
                event_type="user_created",
                target_type="user",
                target_id=str(new_user.id),
                ip_address=ip_address,
                details_json={"username": new_user.username, "assigned_role": data.role},
            )
        )
        await session.commit()
        return new_user, data.role

    @classmethod
    async def create_invitation(
        cls,
        session: AsyncSession,
        data: InvitationCreateRequest,
        creator: User,
        ip_address: Optional[str] = None,
    ) -> InvitationOut:
        """Issue a cryptographically secure single-use invitation link."""
        caller_roles = await cls.get_user_roles(session, creator.id)
        if "SUPER_ADMIN" not in caller_roles and "ADMINISTRATOR" not in caller_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission Denied: Only administrators can issue invitations.",
            )

        roles = await cls.ensure_default_roles(session)
        target_role = roles.get(data.role)
        if not target_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{data.role}'.",
            )

        raw_token = generate_invitation_token()
        token_hash = hash_invitation_token(raw_token)

        invitation = Invitation(
            email=data.email.lower().strip(),
            role_id=target_role.id,
            token_hash=token_hash,
            invited_by=creator.id,
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(invitation)

        session.add(
            AuditEvent(
                workspace_id=data.workspace_id,
                actor_id=creator.id,
                actor_type="user",
                event_type="invitation_created",
                target_type="invitation",
                target_id=str(invitation.id),
                ip_address=ip_address,
                details_json={"email": invitation.email, "role": data.role},
            )
        )
        await session.commit()

        return InvitationOut(
            id=invitation.id,
            email=invitation.email,
            role=data.role,
            status="pending",
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            invitation_token=raw_token,
            invitation_url=f"/auth/accept-invitation?token={raw_token}",
        )

    @classmethod
    async def accept_invitation(
        cls,
        session: AsyncSession,
        data: InvitationAcceptRequest,
        ip_address: Optional[str] = None,
    ) -> User:
        """Redeem invitation token and activate new user account."""
        token_hash = hash_invitation_token(data.token)
        stmt = (
            select(Invitation)
            .where(Invitation.token_hash == token_hash)
            .options(selectinload(Invitation.role))
        )
        invitation = await session.scalar(stmt)
        if not invitation or not invitation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or already redeemed invitation token.",
            )

        # Check unique username/email
        normalized_username = data.username.lower().strip()
        existing = await session.scalar(
            select(User).where(or_(User.email == invitation.email, User.username == normalized_username))
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this username or email already exists.",
            )

        # Create user
        new_user = User(
            username=normalized_username,
            email=invitation.email,
            display_name=data.display_name.strip(),
            password_hash=hash_password(data.password),
            status="active",
        )
        session.add(new_user)
        await session.flush()

        # Assign role from invitation
        session.add(
            UserRole(
                user_id=new_user.id,
                role_id=invitation.role_id,
                granted_by=invitation.invited_by,
            )
        )

        # Update invitation
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(timezone.utc)

        # Create user workspace
        ws_name = f"{data.display_name.strip()}'s Workspace"
        workspace = Workspace(
            name=ws_name,
            slug=f"{cls._slugify(ws_name)}-{str(uuid.uuid4())[:8]}",
            status="active",
        )
        session.add(workspace)
        await session.flush()

        session.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=new_user.id,
                role=invitation.role.name.lower(),
                status="active",
            )
        )

        session.add(
            AuditEvent(
                workspace_id=workspace.id,
                actor_id=new_user.id,
                actor_type="user",
                event_type="invitation_accepted",
                target_type="user",
                target_id=str(new_user.id),
                ip_address=ip_address,
                details_json={"email": new_user.email, "username": new_user.username},
            )
        )
        await session.commit()
        return new_user

    @classmethod
    async def authenticate_user(
        cls,
        session: AsyncSession,
        username_or_email: str,
        password: str,
        mfa_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[TokenResponse, str]:
        """
        Authenticate user with brute-force lockout, MFA verification, and session creation.
        Returns (TokenResponse, raw_session_token).
        """
        identifier = username_or_email.lower().strip()

        # Lookup user by username or email
        stmt = (
            select(User)
            .where(or_(User.username == identifier, User.email == identifier))
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role),
                selectinload(User.memberships).selectinload(WorkspaceMembership.workspace),
            )
        )
        user = await session.scalar(stmt)

        # Record attempt helper
        async def _log_attempt(success: bool, reason: Optional[str] = None):
            attempt = LoginAttempt(
                username_or_email=identifier,
                ip_address=ip_address,
                user_agent=user_agent,
                successful=success,
                failure_reason=reason,
                attempted_at=datetime.now(timezone.utc),
            )
            session.add(attempt)
            await session.commit()

        if not user or not user.password_hash:
            await _log_attempt(False, "User not found or no password set")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password.",
            )

        # Check account lockout
        if user.is_locked:
            await _log_attempt(False, "Account locked")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to excessive failed attempts. Please try again later.",
            )

        # Check account status (active, suspended, disabled, revoked)
        if user.status != "active":
            await _log_attempt(False, f"Account status: {user.status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status}. Contact your administrator for access.",
            )

        # Verify password (Argon2id or legacy bcrypt)
        if not verify_password(password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await _log_attempt(False, "Password mismatch")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password.",
            )

        # Verify MFA if enabled
        if user.mfa_enabled:
            if not mfa_code:
                # Return temp token indicating MFA required
                temp_token = create_access_token(
                    subject=str(user.id),
                    role="mfa_pending",
                    expires_delta=timedelta(minutes=5),
                )
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,  # Sentinel or handled via separate endpoint
                    detail={
                        "mfa_required": True,
                        "temp_session_token": temp_token,
                        "message": "Multi-Factor Authentication required.",
                    },
                )

            if not verify_mfa_code(user.mfa_secret or "", mfa_code):
                await _log_attempt(False, "Invalid MFA code")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA verification code.",
                )

        # Reset login counters on success
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)

        # Create session in database
        raw_session_token = generate_session_token()
        session_record = Session(
            user_id=user.id,
            session_token_hash=hash_session_token(raw_session_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(session_record)

        await _log_attempt(True)

        # Build CurrentUserOut
        roles_list = [ur.role.name for ur in user.user_roles]
        primary_role = roles_list[0] if roles_list else "INVESTIGATOR"

        memberships_out = [
            WorkspaceMembershipOut(
                workspace_id=m.workspace_id,
                workspace_name=m.workspace.name,
                workspace_slug=m.workspace.slug,
                role=m.role,
                status=m.status,
            )
            for m in user.memberships
            if m.status == "active" and m.workspace.status == "active"
        ]
        active_ws_id = memberships_out[0].workspace_id if memberships_out else None

        user_out = CurrentUserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            roles=roles_list,
            permissions=[],
            mfa_enabled=user.mfa_enabled,
            memberships=memberships_out,
        )

        jwt_token = create_access_token(
            subject=str(user.id),
            workspace_id=str(active_ws_id) if active_ws_id else None,
            role=primary_role,
        )

        token_resp = TokenResponse(
            access_token=jwt_token,
            session_token=raw_session_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_out,
            active_workspace_id=active_ws_id,
        )
        return token_resp, raw_session_token

    @classmethod
    async def logout_user(cls, session: AsyncSession, session_token: Optional[str], user_id: uuid.UUID) -> None:
        """Invalidate session in database."""
        if session_token:
            token_hash = hash_session_token(session_token)
            stmt = select(Session).where(Session.session_token_hash == token_hash)
            sess = await session.scalar(stmt)
            if sess:
                sess.revoked_at = datetime.now(timezone.utc)
                await session.commit()
                return

        # Fallback: revoke all sessions for user
        stmt_all = select(Session).where(and_(Session.user_id == user_id, Session.revoked_at.is_(None)))
        sessions = (await session.scalars(stmt_all)).all()
        for s in sessions:
            s.revoked_at = datetime.now(timezone.utc)
        await session.commit()

    @classmethod
    async def update_user_status(
        cls,
        session: AsyncSession,
        target_user_id: uuid.UUID,
        new_status: str,
        admin: User,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> User:
        """Update account status (active, suspended, disabled, revoked) and revoke sessions if suspended."""
        caller_roles = await cls.get_user_roles(session, admin.id)
        if "SUPER_ADMIN" not in caller_roles and "ADMINISTRATOR" not in caller_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission Denied: Only administrators can modify user status.",
            )

        target_user = await session.scalar(select(User).where(User.id == target_user_id))
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        target_user.status = new_status

        # If suspended, disabled, or revoked: immediately revoke all active sessions
        if new_status in ["suspended", "disabled", "revoked"]:
            active_sessions = (
                await session.scalars(
                    select(Session).where(
                        and_(Session.user_id == target_user_id, Session.revoked_at.is_(None))
                    )
                )
            ).all()
            for s in active_sessions:
                s.revoked_at = datetime.now(timezone.utc)

        session.add(
            AuditEvent(
                actor_id=admin.id,
                actor_type="user",
                event_type="user_status_changed",
                target_type="user",
                target_id=str(target_user_id),
                ip_address=ip_address,
                details_json={"new_status": new_status, "reason": reason},
            )
        )
        await session.commit()
        return target_user

    @classmethod
    async def get_user_roles(cls, session: AsyncSession, user_id: uuid.UUID) -> List[str]:
        """Fetch list of role names assigned to user."""
        stmt = (
            select(UserRole)
            .where(UserRole.user_id == user_id)
            .options(selectinload(UserRole.role))
        )
        user_roles = (await session.scalars(stmt)).all()
        return [ur.role.name for ur in user_roles if ur.role]

    @classmethod
    async def get_current_user_profile(cls, session: AsyncSession, user_id: uuid.UUID) -> CurrentUserOut:
        """Fetch full user profile with roles and workspace memberships."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role),
                selectinload(User.memberships).selectinload(WorkspaceMembership.workspace),
            )
        )
        user = await session.scalar(stmt)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        roles_list = [ur.role.name for ur in user.user_roles]
        memberships_out = [
            WorkspaceMembershipOut(
                workspace_id=m.workspace_id,
                workspace_name=m.workspace.name,
                workspace_slug=m.workspace.slug,
                role=m.role,
                status=m.status,
            )
            for m in user.memberships
            if m.status == "active" and m.workspace.status == "active"
        ]

        return CurrentUserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            roles=roles_list,
            permissions=[],
            mfa_enabled=user.mfa_enabled,
            memberships=memberships_out,
        )

    @classmethod
    async def setup_mfa(cls, session: AsyncSession, user_id: uuid.UUID) -> MFASetupResponse:
        """Generate TOTP secret and provisioning URI."""
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        secret = generate_mfa_secret()
        user.mfa_secret = secret
        await session.commit()

        uri = get_mfa_uri(secret=secret, account_name=user.email)
        return MFASetupResponse(secret=secret, otpauth_uri=uri)

    @classmethod
    async def enable_mfa(cls, session: AsyncSession, user_id: uuid.UUID, mfa_code: str) -> bool:
        """Verify initial TOTP code and enable MFA on user account."""
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user or not user.mfa_secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not initialized.")

        if not verify_mfa_code(user.mfa_secret, mfa_code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code.")

        user.mfa_enabled = True
        user.mfa_enrolled_at = datetime.now(timezone.utc)
        await session.commit()
        return True

    @classmethod
    async def check_tool_permission(
        cls, session: AsyncSession, user_id: uuid.UUID, tool_name: str
    ) -> bool:
        """
        Tool-level authorization check:
        1. SUPER_ADMIN has access to all approved tools.
        2. ADMINISTRATOR and INVESTIGATOR have access to allowed tools unless revoked.
        3. Checks user_tool_permissions table.
        """
        roles = await cls.get_user_roles(session, user_id)
        if "SUPER_ADMIN" in roles:
            return True

        if "ANALYST" in roles and len(roles) == 1:
            return False  # Analyst is read-only

        # Check explicit tool grant/revocation
        tool_stmt = select(Tool).where(Tool.name == tool_name)
        tool = await session.scalar(tool_stmt)
        if not tool:
            return False

        perm_stmt = select(UserToolPermission).where(
            and_(
                UserToolPermission.user_id == user_id,
                UserToolPermission.tool_id == tool.id,
                UserToolPermission.revoked_at.is_(None),
            )
        )
        has_perm = await session.scalar(perm_stmt)
        if has_perm:
            return True

        # Default allowed standard OSINT tools for INVESTIGATOR & ADMINISTRATOR
        return tool_name in ["dns_lookup", "whois_lookup", "public_website_metadata", "playwright_extract"]

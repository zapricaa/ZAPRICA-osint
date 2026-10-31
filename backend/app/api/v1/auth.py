"""Authentication API endpoints for Invite-Only platform."""

from typing import Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.users import User
from app.schemas.auth import (
    BootstrapAdminRequest,
    CurrentUserOut,
    InvitationAcceptRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    TokenResponse,
    UserLogin,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/bootstrap",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="One-time system bootstrap to create initial SUPER_ADMIN",
)
async def bootstrap_super_admin(
    payload: BootstrapAdminRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Initial bootstrap endpoint.
    Permitted ONLY once when no users exist in the database.
    Creates first SUPER_ADMIN and sets HttpOnly session cookie.
    """
    ip_addr = request.client.host if request.client else None
    user, workspace, session_token = await AuthService.bootstrap_super_admin(
        session=db, data=payload, ip_address=ip_addr
    )

    # Set secure HttpOnly session cookie
    is_prod = settings.APP_ENV == "production"
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=7 * 24 * 3600,
    )

    # Return profile & token
    profile = await AuthService.get_current_user_profile(db, user.id)
    from app.core.security import create_access_token
    token = create_access_token(subject=str(user.id), workspace_id=str(workspace.id), role="SUPER_ADMIN")

    return TokenResponse(
        access_token=token,
        session_token=session_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=profile,
        active_workspace_id=workspace.id,
    )


@router.post(
    "/register",
    status_code=status.HTTP_403_FORBIDDEN,
    summary="Public registration endpoint (Disabled by design)",
)
async def disabled_public_registration():
    """Public registration is explicitly disallowed on ZAPRICA."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Public registration is disabled. ZAPRICA is an invite-only platform. Request an administrator invitation.",
    )


@router.post(
    "/accept-invitation",
    response_model=CurrentUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Redeem administrator invitation and activate account",
)
async def accept_invitation(
    payload: InvitationAcceptRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Redeem a valid, unexpired single-use invitation token."""
    ip_addr = request.client.host if request.client else None
    user = await AuthService.accept_invitation(session=db, data=payload, ip_address=ip_addr)
    return await AuthService.get_current_user_profile(db, user.id)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login with MFA verification, lockout protection, and session cookie",
)
async def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username/email + password + optional MFA code."""
    ip_addr = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    token_resp, session_token = await AuthService.authenticate_user(
        session=db,
        username_or_email=payload.username_or_email,
        password=payload.password,
        mfa_code=payload.mfa_code,
        ip_address=ip_addr,
        user_agent=user_agent,
    )

    # Set secure HttpOnly session cookie
    is_prod = settings.APP_ENV == "production"
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=7 * 24 * 3600,
    )

    return token_resp


@router.post("/logout", summary="Logout user and invalidate session")
async def logout(
    response: Response,
    session_token: Optional[str] = Cookie(None, alias="session_token"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invalidate session in database and delete browser cookie."""
    await AuthService.logout_user(session=db, session_token=session_token, user_id=current_user.id)
    response.delete_cookie(key="session_token")
    return {"message": "Logged out successfully. Session invalidated."}


@router.get("/me", response_model=CurrentUserOut, summary="Retrieve current user profile and permissions")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active authenticated user identity and granted roles."""
    return await AuthService.get_current_user_profile(db, current_user.id)


@router.post("/mfa/setup", response_model=MFASetupResponse, summary="Initiate MFA enrollment")
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate TOTP secret and provisioning URI for Google Authenticator / 1Password."""
    return await AuthService.setup_mfa(db, current_user.id)


@router.post("/mfa/enable", summary="Complete MFA enrollment")
async def enable_mfa(
    payload: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify code and turn on MFA enforcement for the account."""
    success = await AuthService.enable_mfa(db, current_user.id, payload.mfa_code)
    return {"mfa_enabled": success, "message": "Multi-Factor Authentication enabled successfully."}

"""Authentication and RBAC Pydantic schemas for Invite-Only platform."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# -------------------------------------------------------------------------
# Login & Session Schemas
# -------------------------------------------------------------------------

class UserLogin(BaseModel):
    """Login payload supporting either username or email with optional MFA code."""
    username_or_email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=6)


class MFARequiredResponse(BaseModel):
    """Response returned when user credentials are valid but MFA verification is needed."""
    mfa_required: bool = True
    temp_session_token: str
    message: str = "Multi-Factor Authentication required. Provide 6-digit TOTP code."


class MFAVerifyRequest(BaseModel):
    """TOTP code submission to complete MFA login or enrollment."""
    temp_session_token: Optional[str] = None
    mfa_code: str = Field(..., min_length=6, max_length=6)


class MFASetupResponse(BaseModel):
    """TOTP provisioning information for authenticator apps."""
    secret: str
    otpauth_uri: str


# -------------------------------------------------------------------------
# User Profiles & Tokens
# -------------------------------------------------------------------------

class WorkspaceMembershipOut(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    workspace_slug: str
    role: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class CurrentUserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    display_name: str
    status: str
    roles: List[str] = []
    permissions: List[str] = []
    mfa_enabled: bool = False
    memberships: List[WorkspaceMembershipOut] = []

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    session_token: Optional[str] = None
    expires_in: int
    user: CurrentUserOut
    active_workspace_id: Optional[uuid.UUID] = None


class UserDetailOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    display_name: str
    status: str
    roles: List[str] = []
    permissions: List[str] = []
    mfa_enabled: bool = False
    failed_login_count: int = 0
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------------
# Administrator User & Invitation Management
# -------------------------------------------------------------------------

class BootstrapAdminRequest(BaseModel):
    """One-time initial bootstrap payload to create the first SUPER_ADMIN."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=12, max_length=128)
    bootstrap_secret: str = Field(..., min_length=8, max_length=128)
    workspace_name: Optional[str] = Field("Primary Workspace", max_length=100)


class AdminUserCreateRequest(BaseModel):
    """Direct administrator user provisioning."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field("INVESTIGATOR", pattern="^(SUPER_ADMIN|ADMINISTRATOR|INVESTIGATOR|ANALYST)$")
    workspace_id: Optional[uuid.UUID] = None


class AdminUserStatusUpdateRequest(BaseModel):
    """Account status transition: active, suspended, disabled, revoked."""
    status: str = Field(..., pattern="^(active|suspended|disabled|revoked)$")
    reason: Optional[str] = None


class AdminUserRoleUpdateRequest(BaseModel):
    """Assign system role to user."""
    role: str = Field(..., pattern="^(SUPER_ADMIN|ADMINISTRATOR|INVESTIGATOR|ANALYST)$")


class InvitationCreateRequest(BaseModel):
    """Create single-use secure invitation token."""
    email: EmailStr
    role: str = Field("INVESTIGATOR", pattern="^(SUPER_ADMIN|ADMINISTRATOR|INVESTIGATOR|ANALYST)$")
    workspace_id: Optional[uuid.UUID] = None


class InvitationAcceptRequest(BaseModel):
    """Redeem invitation and set account password and username."""
    token: str = Field(..., min_length=16)
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    display_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)


class InvitationOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime
    invitation_token: Optional[str] = None
    invitation_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionOut(BaseModel):
    id: uuid.UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    is_active: bool
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


class LoginAttemptOut(BaseModel):
    id: uuid.UUID
    username_or_email: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    successful: bool
    failure_reason: Optional[str] = None
    attempted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserToolPermissionAssignRequest(BaseModel):
    user_id: uuid.UUID
    tool_id: uuid.UUID

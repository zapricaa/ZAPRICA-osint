"""Tests for Authentication, Authorization, Invite-Only Policies, and RBAC."""

import pytest
import uuid
import pyotp
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.models.users import User
from app.models.workspaces import Workspace, WorkspaceMembership
from app.models.rbac import Role, UserRole
from app.models.sessions import Session, LoginAttempt
from app.services.auth_service import AuthService


@pytest.fixture
async def test_db_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.fixture
async def client(test_db_session: AsyncSession):
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ac_auth_01_unauthenticated_user_rejected(client: AsyncClient):
    """AC-AUTH-01: Anonymous users cannot access protected APIs (returns 401)."""
    resp = await client.get("/v1/me")
    assert resp.status_code == 401
    assert "authentication required" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_public_registration_disabled(client: AsyncClient):
    """Registration Policy: No public signup or anonymous registration endpoint."""
    resp = await client.post("/v1/auth/register", json={
        "email": "hacker@example.com",
        "display_name": "Anonymous",
        "password": "Password123!"
    })
    assert resp.status_code == 403
    assert "public registration is disabled" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_one_time_bootstrap_super_admin(client: AsyncClient):
    """One-time bootstrap of the first SUPER_ADMIN account requires valid secret."""
    # 1. Reject invalid bootstrap secret
    invalid_payload = {
        "username": "superadmin",
        "email": "admin@example.com",
        "display_name": "Chief Security Officer",
        "password": "SuperSecureAdminPassword123!",
        "bootstrap_secret": "wrong_secret_key",
        "workspace_name": "HQ Cyber Command"
    }
    resp = await client.post("/v1/auth/bootstrap", json=invalid_payload)
    assert resp.status_code == 403
    assert "invalid bootstrap secret" in resp.json()["detail"].lower()

    # 2. Succeed with valid bootstrap secret
    valid_payload = {
        "username": "superadmin",
        "email": "admin@example.com",
        "display_name": "Chief Security Officer",
        "password": "SuperSecureAdminPassword123!",
        "bootstrap_secret": "zaprica_bootstrap_superadmin_secret",
        "workspace_name": "HQ Cyber Command"
    }
    resp = await client.post("/v1/auth/bootstrap", json=valid_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "superadmin"
    assert "SUPER_ADMIN" in data["user"]["roles"]

    # Verify session cookie was set
    assert "session_token" in resp.cookies or "session_token" in data

    # Attempting to bootstrap a SECOND time must fail with 403
    second_resp = await client.post("/v1/auth/bootstrap", json=valid_payload)
    assert second_resp.status_code == 403
    assert "already been bootstrapped" in second_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_invitation_and_acceptance_flow(client: AsyncClient):
    """Administrators issue invitations and users redeem them to create accounts."""
    # 1. Bootstrap super admin
    boot_resp = await client.post("/v1/auth/bootstrap", json={
        "username": "superadmin2",
        "email": "super2@example.com",
        "display_name": "Super Admin 2",
        "password": "Password123!@#",
        "bootstrap_secret": "zaprica_bootstrap_superadmin_secret",
    })
    admin_token = boot_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Super admin creates invitation for an investigator
    inv_resp = await client.post(
        "/v1/admin/invitations",
        json={"email": "investigator1@example.com", "role": "INVESTIGATOR"},
        headers=admin_headers
    )
    assert inv_resp.status_code == 201
    inv_data = inv_resp.json()
    raw_invite_token = inv_data["invitation_token"]
    assert raw_invite_token is not None

    # 3. Invitee redeems invitation at /v1/auth/accept-invitation
    accept_resp = await client.post("/v1/auth/accept-invitation", json={
        "token": raw_invite_token,
        "username": "inv_user1",
        "display_name": "Lead Field Investigator",
        "password": "InvestigatorPassword123!"
    })
    assert accept_resp.status_code == 201
    user_data = accept_resp.json()
    assert user_data["username"] == "inv_user1"
    assert "INVESTIGATOR" in user_data["roles"]

    # 4. Attempting to re-use redeemed token fails
    reuse_resp = await client.post("/v1/auth/accept-invitation", json={
        "token": raw_invite_token,
        "username": "another_user",
        "display_name": "Another",
        "password": "AnotherPassword123!"
    })
    assert reuse_resp.status_code == 400
    assert "invalid, expired, or already redeemed" in reuse_resp.json()["detail"].lower()

    # 5. New user logs in successfully with username or email
    login_resp = await client.post("/v1/auth/login", json={
        "username_or_email": "inv_user1",
        "password": "InvestigatorPassword123!"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


@pytest.mark.asyncio
async def test_suspended_user_access_revocation(client: AsyncClient):
    """Suspended users cannot log in and have their active sessions revoked."""
    # 1. Bootstrap super admin
    boot_resp = await client.post("/v1/auth/bootstrap", json={
        "username": "superadmin3",
        "email": "super3@example.com",
        "display_name": "Super Admin 3",
        "password": "Password123!@#",
        "bootstrap_secret": "zaprica_bootstrap_superadmin_secret",
    })
    admin_token = boot_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create investigator directly
    user_resp = await client.post(
        "/v1/admin/users",
        json={
            "username": "rogue_user",
            "email": "rogue@example.com",
            "display_name": "Rogue Agent",
            "password": "RoguePassword123!",
            "role": "INVESTIGATOR"
        },
        headers=admin_headers
    )
    assert user_resp.status_code == 201
    rogue_id = user_resp.json()["id"]

    # 3. Rogue user logs in
    login_resp = await client.post("/v1/auth/login", json={
        "username_or_email": "rogue_user",
        "password": "RoguePassword123!"
    })
    assert login_resp.status_code == 200
    rogue_token = login_resp.json()["access_token"]

    # 4. Verify rogue user can access /v1/me
    me_resp = await client.get("/v1/me", headers={"Authorization": f"Bearer {rogue_token}"})
    assert me_resp.status_code == 200

    # 5. Super admin suspends rogue user
    suspend_resp = await client.patch(
        f"/v1/admin/users/{rogue_id}/status",
        json={"status": "suspended", "reason": "Security audit hold"},
        headers=admin_headers
    )
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["status"] == "suspended"

    # 6. Rogue user cannot access /v1/me anymore (403 Forbidden)
    me_blocked = await client.get("/v1/me", headers={"Authorization": f"Bearer {rogue_token}"})
    assert me_blocked.status_code == 403
    assert "suspended" in me_blocked.json()["detail"].lower()

    # 7. Rogue user cannot log in anymore
    login_blocked = await client.post("/v1/auth/login", json={
        "username_or_email": "rogue_user",
        "password": "RoguePassword123!"
    })
    assert login_blocked.status_code == 403
    assert "suspended" in login_blocked.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mfa_setup_and_login_verification(client: AsyncClient):
    """MFA setup, enrollment, and TOTP verification during login."""
    # 1. Bootstrap super admin
    boot_resp = await client.post("/v1/auth/bootstrap", json={
        "username": "mfadmin",
        "email": "mfa@example.com",
        "display_name": "MFA Admin",
        "password": "Password123!@#",
        "bootstrap_secret": "zaprica_bootstrap_superadmin_secret",
    })
    admin_token = boot_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Initiate MFA setup
    setup_resp = await client.post("/v1/auth/mfa/setup", headers=headers)
    assert setup_resp.status_code == 200
    mfa_secret = setup_resp.json()["secret"]
    assert len(mfa_secret) == 32

    # 3. Complete enrollment with valid TOTP code
    totp = pyotp.TOTP(mfa_secret)
    valid_code = totp.now()
    enable_resp = await client.post(
        "/v1/auth/mfa/enable",
        json={"mfa_code": valid_code},
        headers=headers
    )
    assert enable_resp.status_code == 200
    assert enable_resp.json()["mfa_enabled"] is True

    # 4. Login without MFA code raises HTTP 402/special MFA required challenge
    mfa_challenge_resp = await client.post("/v1/auth/login", json={
        "username_or_email": "mfadmin",
        "password": "Password123!@#"
    })
    assert mfa_challenge_resp.status_code in [401, 402]
    detail = mfa_challenge_resp.json()["detail"]
    assert isinstance(detail, dict)
    assert detail.get("mfa_required") is True

    # 5. Login with invalid MFA code fails (401)
    bad_mfa_resp = await client.post("/v1/auth/login", json={
        "username_or_email": "mfadmin",
        "password": "Password123!@#",
        "mfa_code": "000000"
    })
    assert bad_mfa_resp.status_code == 401
    assert "invalid mfa" in bad_mfa_resp.json()["detail"].lower()

    # 6. Login with valid MFA code succeeds
    fresh_code = totp.now()
    good_mfa_resp = await client.post("/v1/auth/login", json={
        "username_or_email": "mfadmin",
        "password": "Password123!@#",
        "mfa_code": fresh_code
    })
    assert good_mfa_resp.status_code == 200
    assert "access_token" in good_mfa_resp.json()


@pytest.mark.asyncio
async def test_logout_invalidates_session(client: AsyncClient):
    """Logout invalidates the active database session."""
    boot_resp = await client.post("/v1/auth/bootstrap", json={
        "username": "logoutuser",
        "email": "logout@example.com",
        "display_name": "Logout User",
        "password": "Password123!@#",
        "bootstrap_secret": "zaprica_bootstrap_superadmin_secret",
    })
    token = boot_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify authenticated
    me_resp = await client.get("/v1/me", headers=headers)
    assert me_resp.status_code == 200

    # Logout
    logout_resp = await client.post("/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert "logged out" in logout_resp.json()["message"].lower()

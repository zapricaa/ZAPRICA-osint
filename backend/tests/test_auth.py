import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.models.users import User
from app.models.workspaces import Workspace, WorkspaceMembership


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
    # Liveness
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Readiness
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ac_auth_01_unauthenticated_user_rejected(client: AsyncClient):
    """AC-AUTH-01: Unauthenticated user cannot access protected endpoints (returns 401)."""
    resp = await client.get("/v1/me")
    assert resp.status_code == 401
    assert "credential required" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_registration_and_login_flow(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "analyst@example.com",
        "display_name": "Cyber Analyst",
        "password": "SecurePassword123!",
        "workspace_name": "Threat Intel Ops"
    }
    resp = await client.post("/v1/auth/register", json=reg_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "analyst@example.com"
    assert len(data["user"]["memberships"]) == 1
    assert data["user"]["memberships"][0]["role"] == "admin"

    token = data["access_token"]
    ws_id = data["user"]["memberships"][0]["workspace_id"]

    # 2. Access /v1/me with Token
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}
    resp_me = await client.get("/v1/me", headers=headers)
    assert resp_me.status_code == 200
    me_data = resp_me.json()
    assert me_data["email"] == "analyst@example.com"

    # 3. Login with correct credentials
    login_payload = {
        "email": "analyst@example.com",
        "password": "SecurePassword123!"
    }
    resp_login = await client.post("/v1/auth/login", json=login_payload)
    assert resp_login.status_code == 200
    assert "access_token" in resp_login.json()

    # 4. Login with wrong password
    bad_login = {
        "email": "analyst@example.com",
        "password": "WrongPassword!"
    }
    resp_bad = await client.post("/v1/auth/login", json=bad_login)
    assert resp_bad.status_code == 401


@pytest.mark.asyncio
async def test_ac_auth_02_cross_workspace_isolation(client: AsyncClient, test_db_session: AsyncSession):
    """AC-AUTH-02: User cannot access another workspace's resource or scope."""
    # Register User A in Workspace A
    user_a_payload = {
        "email": "userA@example.com",
        "display_name": "User A",
        "password": "Password123!",
        "workspace_name": "Workspace Alpha"
    }
    resp_a = await client.post("/v1/auth/register", json=user_a_payload)
    assert resp_a.status_code == 201
    token_a = resp_a.json()["access_token"]

    # Register User B in Workspace B
    user_b_payload = {
        "email": "userB@example.com",
        "display_name": "User B",
        "password": "Password123!",
        "workspace_name": "Workspace Beta"
    }
    resp_b = await client.post("/v1/auth/register", json=user_b_payload)
    assert resp_b.status_code == 201
    ws_b_id = resp_b.json()["user"]["memberships"][0]["workspace_id"]

    # Now User A attempts to operate using Workspace B's ID in header
    from app.api.deps import get_current_workspace, get_current_user
    from fastapi import HTTPException

    user_a = await client.get("/v1/me", headers={"Authorization": f"Bearer {token_a}"})
    assert user_a.status_code == 200

    # User A has no membership in Workspace B
    with pytest.raises(HTTPException) as exc_info:
        authed_user = await get_current_user(
            credentials=type("Creds", (), {"credentials": token_a})(),
            db=test_db_session
        )
        await get_current_workspace(
            user=authed_user,
            x_workspace_id=ws_b_id,
            db=test_db_session
        )
    assert exc_info.value.status_code == 403
    assert "not an authorized member" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_ac_auth_03_role_authorization_restriction(test_db_session: AsyncSession):
    """AC-AUTH-03: User with viewer role cannot perform investigator actions."""
    from app.api.deps import require_role
    from fastapi import HTTPException
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Create workspace and viewer user
    ws = Workspace(name="Test Workspace", slug="test-ws", status="active")
    test_db_session.add(ws)
    await test_db_session.flush()

    user = User(email="viewer@example.com", display_name="Viewer", status="active")
    test_db_session.add(user)
    await test_db_session.flush()

    membership = WorkspaceMembership(workspace_id=ws.id, user_id=user.id, role="viewer", status="active")
    test_db_session.add(membership)
    await test_db_session.commit()

    # Re-query user eagerly with selectinload
    stmt = (
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.memberships).selectinload(WorkspaceMembership.workspace))
    )
    user_loaded = await test_db_session.scalar(stmt)
    assert user_loaded is not None

    # Verify require_role(["admin", "investigator"]) blocks the viewer
    check_investigator = require_role(["admin", "investigator"])
    with pytest.raises(HTTPException) as exc_info:
        await check_investigator(user=user_loaded, workspace=ws)

    assert exc_info.value.status_code == 403
    assert "viewer" in exc_info.value.detail

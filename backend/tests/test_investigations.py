import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db


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


@pytest.fixture
async def auth_headers(client: AsyncClient):
    reg_payload = {
        "username": "investigator_lead",
        "email": "investigator@example.com",
        "display_name": "Senior Investigator",
        "password": "Password123!@#",
        "bootstrap_secret": "zaprica_bootstrap_superadmin_secret",
        "workspace_name": "Investigation Division"
    }
    resp = await client.post("/v1/auth/bootstrap", json=reg_payload)
    data = resp.json()
    token = data["access_token"]
    ws_id = data["user"]["memberships"][0]["workspace_id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}


@pytest.mark.asyncio
async def test_ac_inv_01_create_investigation_with_scope(client: AsyncClient, auth_headers: dict):
    """AC-INV-01: Create an authorized investigation with explicit scope in draft state."""
    payload = {
        "title": "Operation Sovereign Shield",
        "objective": "Gather public intelligence regarding target enterprise web infrastructure",
        "investigation_type": "public_website",
        "priority": "high",
        "scope": {
            "purpose": "Authorized vulnerability and infrastructure reconnaissance",
            "allowed_targets": ["example.com", "subdomain.example.com"],
            "allowed_operations": ["public_website_metadata", "content_extraction"],
            "denied_targets": ["internal.example.com", "192.168.1.0/24"]
        }
    }
    resp = await client.post("/v1/investigations", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    inv = resp.json()
    assert inv["title"] == "Operation Sovereign Shield"
    assert inv["status"] == "draft"
    assert inv["priority"] == "high"
    assert inv["scope"] is not None
    assert "example.com" in inv["scope"]["allowed_targets"]
    assert "subdomain.example.com" in inv["scope"]["allowed_targets"]


@pytest.mark.asyncio
async def test_ac_inv_02_reject_empty_or_malformed_scope(client: AsyncClient, auth_headers: dict):
    """AC-INV-02: Reject empty or malformed scope."""
    # 1. Empty targets list
    empty_payload = {
        "title": "Invalid Investigation",
        "objective": "Testing invalid targets",
        "scope": {
            "purpose": "Test",
            "allowed_targets": []
        }
    }
    resp1 = await client.post("/v1/investigations", json=empty_payload, headers=auth_headers)
    assert resp1.status_code == 400

    # 2. Malformed targets (invalid syntax)
    bad_payload = {
        "title": "Invalid Target Investigation",
        "objective": "Testing invalid targets",
        "scope": {
            "purpose": "Valid purpose testing invalid target format",
            "allowed_targets": ["not a valid target@@@!!!"]
        }
    }
    resp2 = await client.post("/v1/investigations", json=bad_payload, headers=auth_headers)
    assert resp2.status_code == 400
    assert "invalid target format" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_investigation_lifecycle_controls(client: AsyncClient, auth_headers: dict):
    """Test start, pause, resume, and cancel lifecycle."""
    # Create investigation
    payload = {
        "title": "Lifecycle Test Investigation",
        "objective": "Lifecycle test",
        "scope": {
            "purpose": "Lifecycle test",
            "allowed_targets": ["test.org"]
        }
    }
    create_resp = await client.post("/v1/investigations", json=payload, headers=auth_headers)
    inv_id = create_resp.json()["id"]

    # 1. Start investigation
    start_resp = await client.post(f"/v1/investigations/{inv_id}/start", headers=auth_headers)
    assert start_resp.status_code == 202
    assert start_resp.json()["status"] == "queued"

    # Verify status in GET
    get_resp = await client.get(f"/v1/investigations/{inv_id}", headers=auth_headers)
    assert get_resp.json()["status"] in ["queued", "running", "completed"]

    # 2. Pause investigation
    pause_resp = await client.post(f"/v1/investigations/{inv_id}/pause", headers=auth_headers)
    assert pause_resp.status_code == 202
    assert pause_resp.json()["status"] == "paused"

    # 3. Resume investigation
    resume_resp = await client.post(f"/v1/investigations/{inv_id}/resume", headers=auth_headers)
    assert resume_resp.status_code == 202
    assert resume_resp.json()["status"] == "running"

    # 4. Cancel investigation
    cancel_resp = await client.post(f"/v1/investigations/{inv_id}/cancel", headers=auth_headers)
    assert cancel_resp.status_code == 202
    assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_ac_inv_04_scope_expiry_blocks_start(client: AsyncClient, auth_headers: dict):
    """AC-INV-04: Expired scope blocks starting or resuming an investigation."""
    expired_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    payload = {
        "title": "Expired Scope Investigation",
        "objective": "Expired scope test",
        "scope": {
            "purpose": "Testing expiration",
            "allowed_targets": ["expired.org"],
            "expires_at": expired_time
        }
    }
    create_resp = await client.post("/v1/investigations", json=payload, headers=auth_headers)
    inv_id = create_resp.json()["id"]

    # Attempt to start with expired scope
    start_resp = await client.post(f"/v1/investigations/{inv_id}/start", headers=auth_headers)
    assert start_resp.status_code == 403
    assert "scope has expired" in start_resp.json()["detail"].lower()

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.services.tool_service import ToolService


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
async def admin_headers(client: AsyncClient):
    reg_payload = {
        "email": "admin@example.com",
        "display_name": "Admin Operator",
        "password": "AdminPassword123!",
        "workspace_name": "SecOps Core"
    }
    resp = await client.post("/v1/auth/register", json=reg_payload)
    data = resp.json()
    token = data["access_token"]
    ws_id = data["user"]["memberships"][0]["workspace_id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}


@pytest.mark.asyncio
async def test_ac_tims_01_and_02_new_tool_starts_as_draft(client: AsyncClient, admin_headers: dict):
    """AC-TIMS-01: New tool starts as draft. AC-TIMS-02: Playbook generated from documentation."""
    tool_payload = {
        "tool_key": "shodan_ip_lookup",
        "display_name": "Shodan IP Intelligence",
        "description": "Queries Shodan database for open ports and services",
        "vendor_or_source": "Shodan API",
        "license_id": "Proprietary",
        "version": "1.0.0",
        "execution_type": "api",
        "capabilities": ["network_recon", "port_scan"],
        "documentation_text": "Requires SHODAN_API_KEY environment variable. Query endpoint /shodan/host/{ip}."
    }
    resp = await client.post("/v1/admin/tools", json=tool_payload, headers=admin_headers)
    assert resp.status_code == 201
    tool_ver = resp.json()

    # AC-TIMS-01: Must start as draft
    assert tool_ver["approval_status"] == "draft"

    # AC-TIMS-02: Playbook markdown generated
    assert "# Playbook: Shodan IP Intelligence" in tool_ver["playbook_markdown"]
    assert "network_recon" in tool_ver["playbook_markdown"]


@pytest.mark.asyncio
async def test_ac_tims_03_04_06_lifecycle_validation_and_approval(client: AsyncClient, admin_headers: dict):
    """
    AC-TIMS-03: Isolated validation passes.
    AC-TIMS-04: Approval is separate from validation.
    AC-TIMS-06: Disabling/revocation immediately updates status.
    """
    # 1. Create Tool Draft
    tool_payload = {
        "tool_key": "sublist3r_recon",
        "display_name": "Subdomain Enumeration Tool",
        "description": "Enumerates subdomains using search engines and public archives",
        "vendor_or_source": "OpenSource",
        "version": "1.0.0",
        "execution_type": "terminal",
        "capabilities": ["subdomain_enum"]
    }
    create_resp = await client.post("/v1/admin/tools", json=tool_payload, headers=admin_headers)
    data = create_resp.json()
    tool_id = data["tool_id"]
    version_id = data["id"]

    # 2. AC-TIMS-03: Validate tool in isolation
    val_resp = await client.post(
        f"/v1/admin/tools/{tool_id}/versions/{version_id}/validate",
        headers=admin_headers
    )
    assert val_resp.status_code == 202
    assert val_resp.json()["tests_passed"] is True
    assert val_resp.json()["approval_status"] == "pending_review"

    # 3. AC-TIMS-04: Administrator Human Approval
    app_resp = await client.post(
        f"/v1/admin/tools/{tool_id}/versions/{version_id}/approve",
        headers=admin_headers
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["approval_status"] == "approved"

    # 4. Publish
    pub_resp = await client.post(
        f"/v1/admin/tools/{tool_id}/versions/{version_id}/publish",
        headers=admin_headers
    )
    assert pub_resp.status_code == 200
    assert pub_resp.json()["approval_status"] == "published"

    # 5. Check tool is now discovered by agents (AC-TIMS-05)
    tools_resp = await client.get("/v1/tools?capability=subdomain_enum", headers=admin_headers)
    assert tools_resp.status_code == 200
    assert len(tools_resp.json()) == 1
    assert tools_resp.json()[0]["tool_key"] == "sublist3r_recon"

    # 6. AC-TIMS-06: Disable tool
    dis_resp = await client.post(
        f"/v1/admin/tools/{tool_id}/versions/{version_id}/disable",
        headers=admin_headers
    )
    assert dis_resp.status_code == 200
    assert dis_resp.json()["approval_status"] == "disabled"

    # Verify tool is no longer available to agents
    tools_after = await client.get("/v1/tools?capability=subdomain_enum", headers=admin_headers)
    assert len(tools_after.json()) == 0

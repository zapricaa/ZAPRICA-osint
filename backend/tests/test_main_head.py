import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base
from app.models.workspaces import Workspace
from app.models.users import User
from app.models.investigations import Investigation, InvestigationScope
from app.services.investigation_service import InvestigationService
from app.agents.contracts import TaskEnvelope, FindingsPackage


@pytest.fixture
async def session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as sess:
        yield sess

    await test_engine.dispose()


@pytest.fixture
async def setup_data(session: AsyncSession):
    ws = Workspace(name="Main Head Unit", slug="main-head-test", status="active")
    session.add(ws)
    await session.flush()

    user = User(email="supervisor@example.com", display_name="Supervisor", status="active")
    session.add(user)
    await session.flush()

    inv = Investigation(
        workspace_id=ws.id,
        created_by=user.id,
        title="Main Head Recon Test",
        objective="Analyze target surface",
        status="draft"
    )
    session.add(inv)
    await session.flush()

    scope = InvestigationScope(
        investigation_id=inv.id,
        workspace_id=ws.id,
        purpose="Authorized OSINT test",
        allowed_targets=["example.com"],
        allowed_operations=["public_website_metadata", "dns_lookup"]
    )
    session.add(scope)
    await session.commit()

    return ws, user, inv, scope


@pytest.mark.asyncio
async def test_ac_main_01_02_03_end_to_end_orchestration(session: AsyncSession, setup_data):
    """
    AC-MAIN-01: Main Head creates structured plan.
    AC-MAIN-02: Browser tasks route to Browser Head.
    AC-MAIN-03: Terminal tasks route to Terminal Head.
    """
    ws, user, inv, scope = setup_data

    # Execute LangGraph orchestration
    final_state = await InvestigationService.execute_graph(
        session=session,
        workspace_id=ws.id,
        user_id=user.id,
        investigation_id=inv.id
    )

    # AC-MAIN-01: Structured Plan verification
    assert final_state["status"] == "completed"
    assert "plan" in final_state
    assert final_state["plan"]["understanding"] is not None

    # AC-MAIN-02 & AC-MAIN-03: Task Routing
    tasks = final_state["tasks"]
    assert len(tasks) >= 2

    browser_tasks = [t for t in tasks if t["assigned_agent"] == "browser_head"]
    terminal_tasks = [t for t in tasks if t["assigned_agent"] == "terminal_head"]

    assert len(browser_tasks) >= 1
    assert len(terminal_tasks) >= 1

    # Verify report was synthesized
    assert final_state.get("report_id") is not None


@pytest.mark.asyncio
async def test_ac_main_04_llm_cannot_expand_scope(session: AsyncSession, setup_data):
    """AC-MAIN-04: Targets outside approved scope are rejected by Scope Gate."""
    ws, user, inv, scope = setup_data

    from app.agents.main_head.graph import MainHeadGraphRunner
    runner = MainHeadGraphRunner.build_graph(session)

    # Attempt to run with an out-of-scope target
    unauthorized_state = {
        "investigation_id": str(inv.id),
        "workspace_id": str(ws.id),
        "user_id": str(user.id),
        "target": "malicious-unauthorized-target.org",  # NOT in scope
        "objective": "Attempt unauthorized reconnaissance",
        "scope": {
            "allowed_targets": ["example.com"],
            "purpose": "Authorized scope only"
        },
        "plan": {},
        "tasks": [],
        "findings_packages": [],
        "consolidated_findings": [],
        "report_id": None,
        "status": "queued",
        "errors": [],
        "audit_events": []
    }

    result = await runner.ainvoke(unauthorized_state)
    assert result["status"] == "failed"
    assert any("not within authorized investigation scope" in err for err in result["errors"])

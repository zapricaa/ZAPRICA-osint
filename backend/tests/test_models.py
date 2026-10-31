import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base
from app.models import (
    Workspace,
    WorkspaceMembership,
    User,
    Investigation,
    InvestigationScope,
    Task,
    Tool,
    ToolVersion,
    AgentToolAssignment,
    EvidenceArtifact,
    Finding,
    FindingSource,
    Report,
    AuditEvent,
)


@pytest.fixture
async def async_session():
    # Use in-memory SQLite with aiosqlite for hermetic testing
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_create_workspace_and_user(async_session: AsyncSession):
    # 1. Create Workspace
    workspace = Workspace(
        name="Cyber Ops Unit",
        slug="cyber-ops",
        status="active"
    )
    async_session.add(workspace)
    await async_session.flush()

    assert workspace.id is not None

    # 2. Create User
    user = User(
        email="operator@zaprica.local",
        display_name="Lead Investigator",
        password_hash="hashed_secret",
        status="active"
    )
    async_session.add(user)
    await async_session.flush()

    assert user.id is not None

    # 3. Create WorkspaceMembership
    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=user.id,
        role="admin",
        status="active"
    )
    async_session.add(membership)
    await async_session.flush()

    # 4. Create Investigation with Scope
    investigation = Investigation(
        workspace_id=workspace.id,
        created_by=user.id,
        title="Target Domain OSINT",
        objective="Assess public web attack surface and infrastructure of example.com",
        investigation_type="public_website",
        status="draft",
        priority="medium"
    )
    async_session.add(investigation)
    await async_session.flush()

    scope = InvestigationScope(
        investigation_id=investigation.id,
        workspace_id=workspace.id,
        purpose="Authorized OSINT assessment",
        allowed_targets=["example.com", "*.example.com"],
        allowed_operations=["public_website_metadata", "dns_lookup"],
        denied_targets=["internal.example.com", "10.0.0.0/8"]
    )
    async_session.add(scope)
    await async_session.flush()

    assert investigation.id is not None
    assert scope.id is not None

    # 5. Create Task
    task = Task(
        workspace_id=workspace.id,
        investigation_id=investigation.id,
        requesting_agent="main_head",
        assigned_agent="browser_head",
        capability="public_website_metadata",
        objective="Extract homepage metadata and technology stack",
        input_json={"target": "example.com"},
        allowed_tool_ids=["website_metadata"]
    )
    async_session.add(task)
    await async_session.flush()

    # 6. Create Evidence Artifact
    artifact = EvidenceArtifact(
        workspace_id=workspace.id,
        investigation_id=investigation.id,
        task_id=task.id,
        storage_uri="local://data/evidence/art1.html",
        media_type="text/html",
        byte_size=1024,
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        source_url="https://example.com",
        collected_by="browser_worker"
    )
    async_session.add(artifact)
    await async_session.flush()

    # 7. Create Finding linked to Evidence
    finding = Finding(
        workspace_id=workspace.id,
        investigation_id=investigation.id,
        task_id=task.id,
        finding_type="tech_stack",
        title="Web Server Identified",
        summary="Server runs NGINX 1.24",
        normalized_value="nginx/1.24",
        verification_status="supported",
        confidence_level="high",
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc)
    )
    async_session.add(finding)
    await async_session.flush()

    source = FindingSource(
        finding_id=finding.id,
        evidence_artifact_id=artifact.id,
        source_url="https://example.com",
        relationship="supports"
    )
    async_session.add(source)
    await async_session.flush()

    # 8. Create Report
    report = Report(
        workspace_id=workspace.id,
        investigation_id=investigation.id,
        version=1,
        status="generated",
        title="OSINT Report - example.com",
        summary="Assessment completed with 1 supported finding.",
        report_json={"findings_count": 1}
    )
    async_session.add(report)
    await async_session.flush()

    # 9. Create Audit Event
    audit = AuditEvent(
        workspace_id=workspace.id,
        actor_type="user",
        actor_id=str(user.id),
        action="investigation_created",
        resource_type="investigation",
        resource_id=investigation.id,
        decision="allow"
    )
    async_session.add(audit)
    await async_session.commit()

    assert report.id is not None
    assert audit.id is not None

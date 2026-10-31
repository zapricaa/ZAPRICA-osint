"""Tests for Report generation, provenance linking, facts vs inferences, and exports."""

import json
import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.workspaces import Workspace
from app.models.users import User
from app.models.investigations import Investigation, InvestigationScope
from app.models.evidence import Finding, FindingSource, EvidenceArtifact
from app.services.report_service import ReportService


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
async def setup_report_data(session: AsyncSession):
    ws = Workspace(name="Report Workspace", slug="report-ws", status="active")
    session.add(ws)
    await session.flush()

    user = User(email="analyst@example.com", display_name="Lead Analyst", status="active")
    session.add(user)
    await session.flush()

    inv = Investigation(
        workspace_id=ws.id,
        created_by=user.id,
        title="Target Infrastructure Report",
        objective="Analyze attack surface and registration details",
        status="completed"
    )
    session.add(inv)
    await session.flush()

    scope = InvestigationScope(
        investigation_id=inv.id,
        workspace_id=ws.id,
        purpose="Authorized report verification",
        allowed_targets=["example.com"],
        allowed_operations=["dns_lookup", "whois_lookup", "web_metadata"]
    )
    session.add(scope)
    await session.flush()

    # Evidence Artifacts
    art1 = EvidenceArtifact(
        workspace_id=ws.id,
        investigation_id=inv.id,
        storage_uri="local://evidence/dns.json",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        byte_size=128,
        media_type="application/json",
        collected_by="terminal_worker",
        created_at=datetime.now(timezone.utc)
    )
    session.add(art1)
    await session.flush()

    # Finding 1: High confidence (Observed Fact) with source provenance (AC-REPORT-01, AC-REPORT-02)
    f1 = Finding(
        workspace_id=ws.id,
        investigation_id=inv.id,
        finding_type="network",
        title="Apex IP Address",
        normalized_value="93.184.216.34",
        summary="Target resolves to static IPv4",
        confidence_level="high",
        verification_status="supported",
        created_at=datetime.now(timezone.utc)
    )
    session.add(f1)
    await session.flush()

    s1 = FindingSource(
        finding_id=f1.id,
        evidence_artifact_id=art1.id,
        source_url="dns://8.8.8.8",
        source_locator="dns.records[0]",
        relationship="primary_evidence",
        observed_at=datetime.now(timezone.utc)
    )
    session.add(s1)

    # Finding 2: Low confidence / unverified inference (Hypothesis / Inference) (AC-REPORT-01)
    f2 = Finding(
        workspace_id=ws.id,
        investigation_id=inv.id,
        finding_type="organization",
        title="Probable Host Provider",
        normalized_value="Edgecast Networks",
        summary="IP range allocation indicates CDN usage",
        confidence_level="low",
        verification_status="unverified",
        created_at=datetime.now(timezone.utc)
    )
    session.add(f2)
    await session.flush()

    s2 = FindingSource(
        finding_id=f2.id,
        evidence_artifact_id=art1.id,
        source_url="https://bgp.he.net/ip/93.184.216.34",
        source_locator="bgp_prefix_lookup",
        relationship="inference_basis",
        observed_at=datetime.now(timezone.utc)
    )
    session.add(s2)

    await session.commit()
    return ws, user, inv, f1, f2, art1


@pytest.mark.asyncio
async def test_ac_report_01_separation_of_facts_and_inferences(session: AsyncSession, setup_report_data):
    """AC-REPORT-01: Report must explicitly separate verified facts from hypotheses/inferences."""
    ws, user, inv, f1, f2, _ = setup_report_data

    report = await ReportService.generate_investigation_report(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id
    )

    assert report.status == "finalized"
    report_data = report.report_json

    # Observed facts must include high-confidence/verified finding
    observed_titles = [item["title"] for item in report_data["observed_facts"]]
    assert "Apex IP Address" in observed_titles
    assert "Probable Host Provider" not in observed_titles

    # Inferred findings must include low-confidence/unverified finding
    inferred_titles = [item["title"] for item in report_data["inferred_findings"]]
    assert "Probable Host Provider" in inferred_titles
    assert "Apex IP Address" not in inferred_titles


@pytest.mark.asyncio
async def test_ac_report_02_provenance_links_in_report(session: AsyncSession, setup_report_data):
    """AC-REPORT-02: Every reported fact must include source URLs and locators."""
    ws, user, inv, f1, _, _ = setup_report_data

    report = await ReportService.generate_investigation_report(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id
    )

    observed = report.report_json["observed_facts"]
    fact = next(item for item in observed if item["title"] == "Apex IP Address")

    assert len(fact["sources"]) >= 1
    assert fact["sources"][0]["source_url"] == "dns://8.8.8.8"
    assert fact["sources"][0]["source_locator"] == "dns.records[0]"
    assert fact["sources"][0]["observed_at"] is not None


@pytest.mark.asyncio
async def test_ac_report_03_partial_investigation_warning(session: AsyncSession, setup_report_data):
    """AC-REPORT-03: Reports generated on non-completed investigations must be explicitly marked as partial."""
    ws, user, inv, _, _, _ = setup_report_data

    # Set status to running (incomplete)
    inv.status = "running"
    await session.commit()

    report = await ReportService.generate_investigation_report(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id
    )

    assert report.status == "partial"
    assert report.report_json["is_partial_report"] is True
    assert "partial observations" in report.report_json["limitations"]
    assert report.finalized_at is None


@pytest.mark.asyncio
async def test_ac_evd_04_cross_source_conflict_detection(session: AsyncSession, setup_report_data):
    """AC-EVD-04: Discrepancies between sources for the same attribute are flagged as conflicts."""
    ws, user, inv, _, _, art1 = setup_report_data

    # Add two conflicting findings for registrant name
    f_whois1 = Finding(
        workspace_id=ws.id,
        investigation_id=inv.id,
        finding_type="whois",
        title="Registrant Organization",
        normalized_value="IANA Reserved",
        summary="Source 1 WHOIS",
        confidence_level="high",
        verification_status="supported",
        created_at=datetime.now(timezone.utc)
    )
    f_whois2 = Finding(
        workspace_id=ws.id,
        investigation_id=inv.id,
        finding_type="whois",
        title="Registrant Organization",
        normalized_value="Example Corp LLC",  # Conflicting value!
        summary="Source 2 WHOIS",
        confidence_level="high",
        verification_status="supported",
        created_at=datetime.now(timezone.utc)
    )
    session.add_all([f_whois1, f_whois2])
    await session.commit()

    report = await ReportService.generate_investigation_report(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id
    )

    conflicts = report.report_json["conflicts_detected"]
    assert len(conflicts) >= 1
    assert any("Registrant Organization" in c["attribute"] for c in conflicts)
    assert any("reported 'IANA Reserved' while Source 2 reported 'Example Corp LLC'" in c["conflict_detail"] for c in conflicts)


@pytest.mark.asyncio
async def test_ac_report_04_json_and_csv_exports(session: AsyncSession, setup_report_data):
    """AC-REPORT-04: Authorized users can export reports in valid JSON and CSV formats."""
    ws, user, inv, _, _, _ = setup_report_data

    # Ensure report is generated first
    await ReportService.generate_investigation_report(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id
    )

    # 1. Test JSON Export
    json_str = await ReportService.export_json(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id
    )
    parsed = json.loads(json_str)
    assert "observed_facts" in parsed
    assert "inferred_findings" in parsed

    # 2. Test CSV Export
    csv_str = await ReportService.export_csv(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id
    )
    lines = csv_str.strip().split("\r\n") if "\r\n" in csv_str else csv_str.strip().split("\n")
    assert len(lines) >= 3  # Header + 2 findings
    assert "Finding ID,Type,Title,Normalized Value,Confidence,Status,Sources" in lines[0]
    assert "Apex IP Address" in csv_str
    assert "93.184.216.34" in csv_str

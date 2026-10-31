import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base
from app.models.workspaces import Workspace
from app.models.users import User
from app.models.investigations import Investigation, InvestigationScope
from app.services.evidence_service import EvidenceService
from app.agents.workers.processors import DataCleaner, DataNormalizer, DuplicateDetector, DataClassifier


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
async def setup_investigation(session: AsyncSession):
    ws = Workspace(name="Evidence Test WS", slug="evidence-test", status="active")
    session.add(ws)
    await session.flush()

    user = User(email="secops@example.com", display_name="SecOps Lead", status="active")
    session.add(user)
    await session.flush()

    inv = Investigation(
        workspace_id=ws.id,
        created_by=user.id,
        title="Evidence Acquisition Test",
        objective="Verify evidence storage and provenance integrity",
        status="running"
    )
    session.add(inv)
    await session.commit()
    return ws, user, inv


@pytest.mark.asyncio
async def test_ac_evd_01_evidence_storage_and_integrity(session: AsyncSession, setup_investigation):
    """AC-EVD-01: Raw evidence is immutable and validated with SHA-256 content hash."""
    ws, user, inv = setup_investigation

    raw_html = b"<html><head><title>Target Site</title></head><body><h1>Welcome</h1></body></html>"
    artifact = await EvidenceService.store_evidence(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id,
        data_bytes=raw_html,
        media_type="text/html",
        collected_by="browser_worker",
        source_url="https://example.com/index.html"
    )

    assert artifact.id is not None
    assert artifact.sha256 is not None
    assert artifact.byte_size == len(raw_html)
    assert artifact.integrity_status == "verified"

    # Verify integrity passes
    is_valid = await EvidenceService.verify_artifact_integrity(session, artifact.id)
    assert is_valid is True


@pytest.mark.asyncio
async def test_ac_evd_02_finding_provenance(session: AsyncSession, setup_investigation):
    """AC-EVD-02: Every finding is strictly linked to source evidence and locator."""
    ws, user, inv = setup_investigation

    raw_html = b"<html><body>Server: Nginx/1.24.0</body></html>"
    artifact = await EvidenceService.store_evidence(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id,
        data_bytes=raw_html,
        media_type="text/html",
        collected_by="browser_worker",
        source_url="https://example.com"
    )

    finding = await EvidenceService.process_and_create_finding(
        session=session,
        workspace_id=ws.id,
        investigation_id=inv.id,
        finding_type="tech_stack",
        title="Web Server Identified",
        summary="Server is running NGINX 1.24.0",
        raw_value="nginx/1.24.0",
        evidence_artifact_id=artifact.id,
        source_url="https://example.com",
        source_locator="HTTP Headers / Body",
        confidence_level="high"
    )

    assert finding.id is not None
    assert finding.verification_status == "supported"
    assert len(finding.sources) == 1
    assert finding.sources[0].evidence_artifact_id == artifact.id
    assert finding.sources[0].source_url == "https://example.com"


def test_ac_evd_03_deterministic_cleaning_and_deduplication():
    """AC-EVD-03: Duplicate processing is deterministic and merges sources."""
    # 1. Cleaner tests
    malicious_html = "<script>alert('pwn')</script><style>body{color:red}</style><h1>Clean Header &amp; Content</h1>"
    cleaned = DataCleaner.clean_html_text(malicious_html)
    assert "<script>" not in cleaned
    assert "<style>" not in cleaned
    assert "Clean Header & Content" in cleaned

    # 2. Normalizer tests
    raw_url = "HTTPS://Example.COM:443/products/items/?utm_source=twitter&ref=social&id=123"
    norm_url = DataNormalizer.normalize_url(raw_url)
    assert norm_url == "https://example.com/products/items?id=123"

    norm_domain = DataNormalizer.normalize_domain("https://WWW.Sub.Example.Com:8080/path")
    assert norm_domain == "sub.example.com"

    # 3. Deduplication tests
    findings = [
        {
            "finding_type": "tech_stack",
            "normalized_value": "nginx",
            "title": "Nginx Web Server",
            "sources": [{"source_url": "https://example.com"}]
        },
        {
            "finding_type": "tech_stack",
            "normalized_value": "nginx",
            "title": "Nginx Server v1.24",
            "sources": [{"source_url": "https://sub.example.com"}]
        },
        {
            "finding_type": "contact",
            "normalized_value": "admin@example.com",
            "title": "Contact Admin",
            "sources": [{"source_url": "https://example.com/contact"}]
        }
    ]

    unique_findings, dup_count = DuplicateDetector.deduplicate(findings)
    assert dup_count == 1
    assert len(unique_findings) == 2

    # The nginx finding merged sources from both URLs!
    nginx_finding = next(f for f in unique_findings if f["finding_type"] == "tech_stack")
    assert len(nginx_finding["sources"]) == 2

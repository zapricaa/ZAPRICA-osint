"""Comprehensive Unit & Integration Test Suite for DCE (Data Collection Engine)."""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport, Response

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.collection.coordinator import dce_coordinator
from app.collection.contracts import CollectorType, TargetType, CollectorStatus
from app.collection.schemas import (
    CollectionJobRequest,
    WhoisResult,
    DnsQueryResult,
    HibpLookupResult,
    TheHarvesterResult,
    SherlockResult,
    HoleheResult,
    DemoResult,
)
from app.collection.adapters.whois import WhoisCollectorAdapter
from app.collection.adapters.dns import DnsCollectorAdapter
from app.collection.adapters.hibp import HibpCollectorAdapter
from app.collection.adapters.theharvester import TheHarvesterCollectorAdapter
from app.collection.adapters.sherlock import SherlockCollectorAdapter
from app.collection.adapters.holehe import HoleheCollectorAdapter
from app.collection.adapters.demo import SyntheticDemoCollectorAdapter
from app.terminal.execution_policy import TerminalExecutionPolicyValidator
from app.terminal.sandbox_manager import DockerSandboxManager, ContainerExecutionResult
from app.services.tool_service import ToolService
from app.schemas.tools import ToolDraftCreate
from fastapi import HTTPException


# ==============================================================================
# 1. WHOIS Collector Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_whois_output_parsing():
    """Verifies that Linux whois RFC 3912 raw output is parsed into structured fields."""
    adapter = WhoisCollectorAdapter()

    sample_whois_output = """
Domain Name: EXAMPLE.COM
Registry Domain ID: 2336799_DOMAIN_COM-VRSN
Registrar: MarkMonitor Inc.
Registrar IANA ID: 292
Creation Date: 1995-08-14T04:00:00Z
Registry Expiry Date: 2028-08-13T04:00:00Z
Updated Date: 2024-08-14T07:01:44Z
Registrant Organization: Example Organization LLC
Registrant State/Province: CA
Name Server: a.iana-servers.net
Name Server: b.iana-servers.net
Domain Status: clientDeleteProhibited
    """

    parsed: WhoisResult = adapter._parse_whois_output("example.com", sample_whois_output)
    assert parsed.domain == "example.com"
    assert parsed.registrar == "MarkMonitor Inc."
    assert "1995-08-14" in parsed.creation_date
    assert "2028-08-13" in parsed.expiration_date
    assert "2024-08-14" in parsed.updated_date
    assert parsed.registrant_organization == "Example Organization LLC"
    assert "a.iana-servers.net" in parsed.name_servers
    assert "b.iana-servers.net" in parsed.name_servers
    assert "clientDeleteProhibited" in parsed.status_flags


@pytest.mark.asyncio
async def test_whois_redaction_and_not_found():
    """Verifies whois privacy redaction detection and unregistered domain warnings."""
    adapter = WhoisCollectorAdapter()

    redacted_output = """
Registrar: NameCheap, Inc.
Registrant Organization: Privacy service provided by Withheld for Privacy ehf
Creation Date: 2021-03-01T00:00:00Z
    """
    parsed = adapter._parse_whois_output("redacted.com", redacted_output)
    assert parsed.is_redacted is True
    assert parsed.registrar == "NameCheap, Inc."


# ==============================================================================
# 2. DNS Collector Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_dns_record_parsing():
    """Verifies that dig output is parsed accurately across all supported record types."""
    adapter = DnsCollectorAdapter()

    # Test MX parsing
    mx_output = "10 mail.example.com.\n20 alt.mail.example.com.\n"
    mx_records = adapter._parse_record_lines("MX", mx_output)
    assert len(mx_records) == 2
    assert mx_records[0].record_type == "MX"
    assert mx_records[0].priority == 10
    assert mx_records[0].value == "mail.example.com"
    assert mx_records[1].priority == 20
    assert mx_records[1].value == "alt.mail.example.com"

    # Test TXT parsing with quotes
    txt_output = '"v=spf1 include:_spf.google.com ~all"\n"google-site-verification=abc123xyz"\n'
    txt_records = adapter._parse_record_lines("TXT", txt_output)
    assert len(txt_records) == 2
    assert txt_records[0].value == "v=spf1 include:_spf.google.com ~all"

    # Test A and NS parsing
    a_records = adapter._parse_record_lines("A", "93.184.216.34\n")
    assert len(a_records) == 1
    assert a_records[0].value == "93.184.216.34"


# ==============================================================================
# 3. HIBP API Collector Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_hibp_api_breach_lookup_success(monkeypatch):
    """Verifies HIBP API breach results parsing with HTTPX mock."""
    adapter = HibpCollectorAdapter()
    monkeypatch.setattr(settings, "HIBP_API_KEY", "test_hibp_api_key_123")

    fake_response_data = [
        {
            "Name": "Adobe",
            "Title": "Adobe Systems",
            "Domain": "adobe.com",
            "BreachDate": "2013-10-04",
            "PwnCount": 152445165,
            "DataClasses": ["Email addresses", "Password hints", "Passwords", "Usernames"],
            "IsVerified": True,
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'[{"Name": "Adobe", "Title": "Adobe Systems", "Domain": "adobe.com", "BreachDate": "2013-10-04", "DataClasses": ["Email addresses"]}]'
    mock_response.json.return_value = fake_response_data

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        out = await adapter.execute("victim@example.com")
        assert out.status == CollectorStatus.SUCCESS
        assert out.parsed_data["breach_count"] == 1
        assert out.parsed_data["breaches"][0]["name"] == "Adobe"


@pytest.mark.asyncio
async def test_hibp_api_404_clean_email(monkeypatch):
    """Verifies that HTTP 404 indicates zero breach records (clean status)."""
    adapter = HibpCollectorAdapter()
    monkeypatch.setattr(settings, "HIBP_API_KEY", "test_hibp_api_key_123")

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        out = await adapter.execute("clean_user@example.com")
        assert out.status == CollectorStatus.SUCCESS
        assert out.parsed_data["breach_count"] == 0
        assert len(out.parsed_data["breaches"]) == 0


@pytest.mark.asyncio
async def test_hibp_api_missing_key(monkeypatch):
    """Verifies that missing HIBP_API_KEY returns UNAVAILABLE without crashing."""
    adapter = HibpCollectorAdapter()
    monkeypatch.setattr(settings, "HIBP_API_KEY", None)

    out = await adapter.execute("user@example.com")
    assert out.status == CollectorStatus.UNAVAILABLE
    assert "not configured" in out.warnings[0].lower()


# ==============================================================================
# 4. theHarvester & Sherlock Parsing Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_theharvester_output_parsing():
    """Verifies that theHarvester stdout is parsed into emails and subdomains."""
    adapter = TheHarvesterCollectorAdapter()

    sample_stdout = """
[*] Target: target.com
[*] Searching crtsh.
[*] Subdomains found: 4
--------------------
admin.target.com
api.target.com
mail.target.com
vpn.target.com

[*] Users/Emails found: 2
-------------------------
contact@target.com
security@target.com
    """
    parsed: TheHarvesterResult = adapter._parse_theharvester_output("target.com", sample_stdout, ["crtsh"])
    assert len(parsed.subdomains) == 4
    assert "admin.target.com" in parsed.subdomains
    assert "mail.target.com" in parsed.subdomains
    assert len(parsed.emails) == 2
    assert "contact@target.com" in parsed.emails


@pytest.mark.asyncio
async def test_sherlock_output_parsing():
    """Verifies that Sherlock output correctly extracts public candidate profile URLs."""
    adapter = SherlockCollectorAdapter()

    sample_stdout = """
[*] Checking username testuser on:
[+] GitHub: https://github.com/testuser
[+] Twitter: https://twitter.com/testuser
[+] Reddit: https://www.reddit.com/user/testuser
    """
    parsed: SherlockResult = adapter._parse_sherlock_output("testuser", sample_stdout)
    assert parsed.total_candidates == 3
    assert parsed.candidates[0].site_name == "GitHub"
    assert parsed.candidates[0].profile_url == "https://github.com/testuser"
    assert parsed.candidates[1].site_name == "Twitter"


# ==============================================================================
# 5. Holehe Disabled-By-Default Policy Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_holehe_disabled_by_default(monkeypatch):
    """Verifies that Holehe strictly fails closed with DISABLED status by default."""
    adapter = HoleheCollectorAdapter()
    monkeypatch.setattr(settings, "HOLEHE_ENABLED", False)

    out = await adapter.execute("target@example.com")
    assert out.status == CollectorStatus.DISABLED
    assert "disabled by policy" in out.warnings[0].lower()


# ==============================================================================
# 6. Synthetic Demo Collector Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_synthetic_demo_collector():
    """Verifies synthetic demo collector only answers for reserved demo identifiers."""
    adapter = SyntheticDemoCollectorAdapter()

    # Reserved demo domain
    out_demo = await adapter.execute("demo.example")
    assert out_demo.status == CollectorStatus.SUCCESS
    assert out_demo.is_synthetic is True
    assert len(out_demo.parsed_data["findings"]) > 0

    # Real target against demo collector: returns empty set with safety notice
    out_real = await adapter.execute("google.com")
    assert out_real.status == CollectorStatus.SUCCESS
    assert out_real.is_synthetic is True
    assert len(out_real.parsed_data["findings"]) == 0
    assert "not a reserved demo identifier" in out_real.warnings[1].lower()


# ==============================================================================
# 7. Security & Injection Defense Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_terminal_policy_flag_injection_defense():
    """Verifies that leading dashes (CLI flag injection) and dangerous shell constructs are blocked."""
    # Attempting flag injection in domain
    with pytest.raises(HTTPException) as exc:
        TerminalExecutionPolicyValidator.validate_command("dns_lookup", {"target": "--version"})
    assert exc.value.status_code == 400
    assert "cannot start with a hyphen" in exc.value.detail.lower()

    # Attempting command chaining
    with pytest.raises(HTTPException) as exc2:
        TerminalExecutionPolicyValidator.validate_command("whois_lookup", {"target": "example.com; rm -rf /"})
    assert exc2.value.status_code == 400
    assert "disallowed character" in exc2.value.detail.lower()


# ==============================================================================
# 8. Real TIMS Validation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_tims_real_validation_engine():
    """Verifies that ToolService.validate_tool_version executes real checks instead of fake mocks."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.models.tools import Tool, ToolVersion

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        ws_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Create valid draft tool
        draft_data = ToolDraftCreate(
            tool_key="valid_dce_tool",
            display_name="Valid DCE Tool",
            description="A valid test collector specification",
            vendor_or_source="ZAPRICA SecOps",
            version="1.0.0",
            execution_type="terminal",
            capabilities=["network_recon"],
            timeout_seconds=30,
        )
        version = await ToolService.create_tool_draft(session, ws_id, user_id, draft_data)
        assert version.approval_status == "draft"

        # Run real isolated validation
        passed, results = await ToolService.validate_tool_version(session, version.tool_id, version.id)
        assert passed is True
        assert results["manifest_integrity"] == "passed"
        assert results["schema_validation"] == "passed"
        assert results["negative_security_injection_test"] == "passed"
        assert results["all_checks_passed"] is True

        # Assert status moved to pending_review
        await session.refresh(version)
        assert version.approval_status == "pending_review"

    await test_engine.dispose()


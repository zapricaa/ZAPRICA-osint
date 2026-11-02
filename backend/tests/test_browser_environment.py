"""Automated verification tests for Browser Head dedicated environment & security policies."""

import pytest
import uuid
from fastapi import HTTPException

from app.browser.browser_security import BrowserSecurityValidator
from app.browser.browser_policy import BrowserPolicyEngine, PolicyType
from app.browser.profile_manager import BrowserProfileManager
from app.browser.session_manager import browser_session_manager, BrowserSessionStatus
from app.browser.browser_manager import browser_manager


@pytest.mark.asyncio
async def test_ssrf_egress_security_filter():
    """AC-SEC-01: Verifies private networks, loopback, link-local, and cloud metadata are blocked."""
    # Loopback
    with pytest.raises(HTTPException) as exc:
        BrowserSecurityValidator.validate_target_url("http://127.0.0.1:8080/admin")
    assert exc.value.status_code == 403
    assert "SSRF" in exc.value.detail or "Security" in exc.value.detail

    # Cloud metadata
    with pytest.raises(HTTPException) as exc:
        BrowserSecurityValidator.validate_target_url("http://169.254.169.254/latest/meta-data/")
    assert exc.value.status_code == 403

    # Private RFC 1918
    with pytest.raises(HTTPException) as exc:
        BrowserSecurityValidator.validate_target_url("http://192.168.1.1/router")
    assert exc.value.status_code == 403

    # Disallowed scheme
    with pytest.raises(HTTPException) as exc:
        BrowserSecurityValidator.validate_target_url("file:///etc/passwd")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_epieos_special_handling_policy():
    """Section 2.6: Verifies Epieos is strictly classified as HUMAN_ASSISTED_ONLY."""
    policy = BrowserPolicyEngine.get_policy_for_domain("epieos.com")
    assert policy.policy_type == PolicyType.HUMAN_ASSISTED_ONLY
    assert policy.browser_automation is False
    assert policy.automated_queries is False
    assert policy.automated_extraction is False
    assert policy.manual_user_access is True
    assert policy.manual_result_import is True

    # Attempting automated extraction on Epieos must raise HTTP 403
    with pytest.raises(HTTPException) as exc:
        BrowserPolicyEngine.enforce_action("epieos.com", "automated_extract")
    assert exc.value.status_code == 403
    assert "HUMAN_ASSISTED_ONLY" in exc.value.detail

    # Manual navigation is allowed
    permitted = BrowserPolicyEngine.enforce_action("epieos.com", "manual_navigate")
    assert permitted.manual_user_access is True


@pytest.mark.asyncio
async def test_blocked_domains_policy():
    """Verifies BLOCKED domains (e.g. *.mil) reject all actions."""
    with pytest.raises(HTTPException) as exc:
        BrowserPolicyEngine.enforce_action("army.mil", "manual_navigate")
    assert exc.value.status_code == 403
    assert "BLOCKED" in exc.value.detail


@pytest.mark.asyncio
async def test_browser_profile_isolation():
    """Section 2.2: Verifies profiles are isolated per user outside source repo without path traversal."""
    u1 = uuid.uuid4()
    u2 = uuid.uuid4()

    path1 = BrowserProfileManager.get_user_profile_dir(u1, "investigation_a")
    path2 = BrowserProfileManager.get_user_profile_dir(u2, "investigation_a")

    # Ensure different users have completely different paths
    assert path1 != path2
    assert str(u1) in str(path1)
    assert str(u2) in str(path2)

    # Path traversal attempt is blocked
    with pytest.raises(HTTPException):
        BrowserProfileManager.get_user_profile_dir(u1, "../../etc/shadow")


@pytest.mark.asyncio
async def test_browser_session_state_machine():
    """Section 2.4: Verifies browser session transitions: DISCONNECTED -> READY -> LOGIN_REQUIRED -> USER_AUTHENTICATED."""
    s_id = uuid.uuid4()
    inv_id = uuid.uuid4()
    u_id = uuid.uuid4()
    prof_id = uuid.uuid4()

    # Register
    state = browser_session_manager.register_session(s_id, inv_id, u_id, prof_id)
    assert state.status == BrowserSessionStatus.STARTING

    # Ready
    browser_session_manager.update_status(str(s_id), BrowserSessionStatus.READY, current_url="https://example.com")
    updated = browser_session_manager.get_session(str(s_id))
    assert updated.status == BrowserSessionStatus.READY
    assert updated.current_url == "https://example.com"

    # Login Required
    browser_session_manager.update_status(str(s_id), BrowserSessionStatus.LOGIN_REQUIRED, current_url="https://example.com/login")
    assert browser_session_manager.get_session(str(s_id)).status == BrowserSessionStatus.LOGIN_REQUIRED

    # Confirm authentication
    confirmed = browser_session_manager.confirm_user_authenticated(str(s_id), confirmed_by="operator_alpha")
    assert confirmed.status == BrowserSessionStatus.USER_AUTHENTICATED
    assert confirmed.auth_confirmed is True
    assert confirmed.auth_confirmed_by == "operator_alpha"

    # Stop session
    stopped = browser_session_manager.close_session(str(s_id))
    assert stopped.status == BrowserSessionStatus.STOPPED


@pytest.mark.asyncio
async def test_browser_manager_lifecycle():
    """Section 2.1: Verifies BrowserManager session start, navigation, and teardown."""
    inv_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Start headless browser session for test
    state = await browser_manager.start_session(
        investigation_id=inv_id,
        user_id=user_id,
        headless=True,
    )
    assert state.session_id is not None
    assert state.status == BrowserSessionStatus.READY

    s_id = state.session_id

    # Navigate to example.com (public mock/live domain)
    try:
        nav = await browser_manager.navigate(s_id, "https://example.com")
        assert nav["status"] == "READY"
        assert "example.com" in nav["current_url"]

        # Extract content
        raw_bytes, extracted = await browser_manager.extract_content(s_id)
        assert len(raw_bytes) > 0
        assert "Example" in extracted["title"]

        # Confirm auth
        auth_state = await browser_manager.confirm_authentication(s_id, "test_investigator")
        assert auth_state.status == BrowserSessionStatus.USER_AUTHENTICATED

    finally:
        # Close session cleanly
        await browser_manager.close_session(s_id)
        assert browser_session_manager.get_session(s_id).status == BrowserSessionStatus.STOPPED


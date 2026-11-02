"""Playwright Browser Worker utilizing dedicated BrowserManager persistent context."""

import uuid
from typing import Dict, Any, Tuple, Optional
from app.browser.browser_manager import browser_manager
from app.browser.browser_policy import BrowserPolicyEngine, PolicyType
from app.browser.session_manager import browser_session_manager, BrowserSessionStatus


class PlaywrightBrowserWorker:
    """Dedicated browser worker using Playwright persistent contexts and security enforcement."""

    @classmethod
    async def extract_website_intelligence(
        cls,
        target_url: str,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> Tuple[bytes, Dict[str, Any], Optional[bytes]]:
        """
        Navigates and extracts verified page content using Playwright.
        Returns (raw_html_bytes, extracted_metadata, screenshot_bytes).
        """
        # 1. Ensure an active dedicated browser session exists
        if not session_id or not browser_session_manager.get_session(session_id):
            active_state = await browser_manager.start_session(
                investigation_id=investigation_id,
                user_id=user_id,
            )
            session_id = active_state.session_id

        # 2. Check Website Automation Policy before doing anything
        parsed_domain = target_url.split("://", 1)[1].split("/", 1)[0] if "://" in target_url else target_url
        policy = BrowserPolicyEngine.get_policy_for_domain(parsed_domain)

        # 3. Navigate the persistent Playwright browser
        nav_result = await browser_manager.navigate(
            session_id=session_id,
            target_url=target_url,
            timeout_ms=timeout_seconds * 1000,
        )

        # 4. Handle HUMAN_ASSISTED_ONLY policy (e.g. Epieos, banking, gov sites)
        if policy.policy_type == PolicyType.HUMAN_ASSISTED_ONLY:
            # Mark that manual investigator interaction is needed
            browser_session_manager.update_status(
                session_id=session_id,
                status=BrowserSessionStatus.LOGIN_REQUIRED,
                current_url=nav_result["current_url"],
            )
            raw_placeholder = (
                f"<!-- ZAPRICA HUMAN_ASSISTED_ONLY: Domain {parsed_domain} opened for manual operator access -->"
            ).encode("utf-8")
            metadata = {
                "url": nav_result["current_url"],
                "title": f"Manual Operator Session: {parsed_domain}",
                "policy_type": policy.policy_type.value,
                "human_assisted_required": True,
                "note": policy.notes or "Automated scraping disabled. Awaiting manual investigator workflow.",
                "resolved_ips": nav_result.get("resolved_ips", []),
                "http_status": nav_result.get("http_status", 200),
            }
            # Optional screenshot of login/landing screen for provenance
            screenshot = await browser_manager.capture_screenshot(session_id)
            return raw_placeholder, metadata, screenshot

        # 5. Extract full DOM content and metadata for AUTOMATED_ALLOWED policy
        raw_bytes, extracted = await browser_manager.extract_content(session_id)
        extracted["http_status"] = nav_result.get("http_status", 200)
        extracted["resolved_ips"] = nav_result.get("resolved_ips", [])
        extracted["policy_type"] = policy.policy_type.value

        # 6. Capture full viewport screenshot
        try:
            screenshot_bytes = await browser_manager.capture_screenshot(session_id)
        except Exception:
            screenshot_bytes = None

        return raw_bytes, extracted, screenshot_bytes

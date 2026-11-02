"""Playwright Dedicated Browser Manager: owns browser lifecycle, contexts, pages, and evidence extraction."""

import asyncio
import logging
import os
import re
import uuid
from typing import Dict, Any, Optional, Tuple, List
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
from fastapi import HTTPException, status

from app.core.config import settings
from app.browser.profile_manager import BrowserProfileManager
from app.browser.browser_security import BrowserSecurityValidator
from app.browser.browser_policy import BrowserPolicyEngine, PolicyType
from app.browser.session_manager import browser_session_manager, BrowserSessionStatus, ActiveBrowserSessionState

logger = logging.getLogger("zaprica.browser")


class BrowserManager:
    """Manages live Playwright persistent browser instances, pages, and security enforcement."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._active_pages: Dict[str, Page] = {}
        self._lock = asyncio.Lock()

    async def _ensure_playwright(self) -> Playwright:
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            return self._playwright

    async def start_session(
        self,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_name: str = "default",
        headless: Optional[bool] = None,
    ) -> ActiveBrowserSessionState:
        """
        Launches or attaches a dedicated persistent browser context for an authorized user.
        Uses persistent profile storage outside the git repository.
        """
        pw = await self._ensure_playwright()

        # 1. Resolve isolated browser profile directory
        profile_path = BrowserProfileManager.get_user_profile_dir(user_id, profile_name)
        session_id = uuid.uuid4()
        s_id_str = str(session_id)
        profile_id = uuid.uuid4()

        # 2. Register session state in session manager
        state = browser_session_manager.register_session(
            session_id=session_id,
            investigation_id=investigation_id,
            user_id=user_id,
            profile_id=profile_id,
        )

        # 3. Configure browser launch options
        is_headless = headless if headless is not None else settings.BROWSER_HEADLESS
        args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-blink-features=AutomationControlled",
        ]

        try:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                headless=is_headless,
                viewport={"width": 1280, "height": 800},
                args=args,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 ZAPRICA-Investigator/1.0",
            )

            self._contexts[s_id_str] = context
            page = context.pages[0] if context.pages else await context.new_page()
            self._active_pages[s_id_str] = page

            browser_session_manager.update_status(
                session_id=s_id_str,
                status=BrowserSessionStatus.READY,
                current_url=page.url,
                tab_count=len(context.pages),
            )
            logger.info("Started dedicated browser session %s for user %s (headless=%s)", s_id_str, user_id, is_headless)
            return state

        except Exception as e:
            logger.error("Failed to launch persistent browser session %s: %s", s_id_str, e)
            browser_session_manager.update_status(
                session_id=s_id_str,
                status=BrowserSessionStatus.ERROR,
                error_message=str(e),
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start browser: {str(e)}")

    async def navigate(
        self,
        session_id: str,
        target_url: str,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        """
        Navigates the dedicated browser session to a target URL with SSRF and automation policy checks.
        """
        # 1. SSRF & Network Validation
        hostname, resolved_ips = BrowserSecurityValidator.validate_target_url(target_url)

        # 2. Automation Policy Check
        policy = BrowserPolicyEngine.enforce_action(hostname, "manual_navigate")

        page = self._active_pages.get(session_id)
        if not page:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Active browser page for session '{session_id}' not found.")

        browser_session_manager.update_status(
            session_id=session_id,
            status=BrowserSessionStatus.BUSY,
            current_url=target_url,
        )

        try:
            response = await page.goto(target_url, wait_until=wait_until, timeout=timeout_ms)
            final_url = page.url

            # Re-verify final URL after redirects for SSRF
            if final_url != target_url:
                BrowserSecurityValidator.validate_target_url(final_url)

            # Check if domain is marked as requiring manual user authentication
            next_status = (
                BrowserSessionStatus.LOGIN_REQUIRED
                if "login" in final_url.lower() or "signin" in final_url.lower()
                else BrowserSessionStatus.READY
            )

            browser_session_manager.update_status(
                session_id=session_id,
                status=next_status,
                current_url=final_url,
                tab_count=len(page.context.pages),
            )

            return {
                "session_id": session_id,
                "current_url": final_url,
                "http_status": response.status if response else 200,
                "policy_type": policy.policy_type.value,
                "resolved_ips": resolved_ips,
                "status": next_status.value,
            }

        except Exception as e:
            browser_session_manager.update_status(
                session_id=session_id,
                status=BrowserSessionStatus.ERROR,
                error_message=str(e),
            )
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Browser navigation failed: {str(e)}")

    async def extract_content(self, session_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Extracts verified webpage content, metadata, and tech stack indicators.
        Strictly blocks automated extraction if the website automation policy is HUMAN_ASSISTED_ONLY or BLOCKED.
        """
        page = self._active_pages.get(session_id)
        if not page:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Active browser page for session '{session_id}' not found.")

        current_url = page.url
        parsed_domain = current_url.split("://", 1)[1].split("/", 1)[0] if "://" in current_url else current_url

        # Check Automation Policy - Epieos and other human-assisted sites strictly block automated extraction
        BrowserPolicyEngine.enforce_action(parsed_domain, "automated_extract")

        html_content = await page.content()
        title = await page.title()
        raw_bytes = html_content.encode("utf-8")

        extracted_metadata = self._parse_dom(html_content, title, current_url)
        return raw_bytes, extracted_metadata

    async def capture_screenshot(self, session_id: str) -> bytes:
        """Captures viewport screenshot as immutable evidence."""
        page = self._active_pages.get(session_id)
        if not page:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Active browser page for session '{session_id}' not found.")

        screenshot_bytes = await page.screenshot(type="png", full_page=False)
        return screenshot_bytes

    async def confirm_authentication(self, session_id: str, operator_username: str) -> ActiveBrowserSessionState:
        """Operator explicitly marks that they have completed manual login & MFA challenges inside the browser."""
        state = browser_session_manager.confirm_user_authenticated(session_id, confirmed_by=operator_username)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Browser session '{session_id}' not found.")
        logger.info("User authentication confirmed for browser session %s by operator %s", session_id, operator_username)
        return state

    async def close_session(self, session_id: str) -> None:
        """Closes browser context and cleans up memory."""
        context = self._contexts.pop(session_id, None)
        self._active_pages.pop(session_id, None)

        if context:
            try:
                await context.close()
            except Exception as e:
                logger.warning("Error closing browser context %s: %s", session_id, e)

        browser_session_manager.close_session(session_id)
        logger.info("Closed browser session %s", session_id)

    def _parse_dom(self, html_content: str, title: str, current_url: str) -> Dict[str, Any]:
        """Parses HTML DOM elements for OSINT intelligence."""
        metadata: Dict[str, Any] = {
            "url": current_url,
            "title": title,
            "meta_tags": {},
            "tech_stack": [],
            "contacts": [],
            "external_links": [],
            "headings": [],
        }

        # Meta tags
        meta_matches = re.findall(r'<meta\s+([^>]+)>', html_content, re.IGNORECASE)
        for meta in meta_matches:
            name_match = re.search(r'(?:name|property)\s*=\s*["\']([^"\']+)["\']', meta, re.IGNORECASE)
            content_match = re.search(r'content\s*=\s*["\']([^"\']+)["\']', meta, re.IGNORECASE)
            if name_match and content_match:
                name = name_match.group(1).strip()
                content = content_match.group(1).strip()
                metadata["meta_tags"][name] = content
                if name.lower() in ("generator", "author", "copyright"):
                    metadata["tech_stack"].append({"type": name.lower(), "value": content})

        # Contacts (emails)
        emails = set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html_content))
        for email in emails:
            if not email.endswith(".png") and not email.endswith(".jpg") and not email.endswith(".svg"):
                metadata["contacts"].append({"type": "email", "value": email})

        # Headings (h1)
        h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
        for h1 in h1s:
            clean = re.sub(r'<[^>]+>', '', h1).strip()
            if clean:
                metadata["headings"].append(clean)

        # External links
        links = set(re.findall(r'href\s*=\s*["\'](https?://[^"\']+)["\']', html_content, re.IGNORECASE))
        for link in list(links)[:20]:
            metadata["external_links"].append(link)

        return metadata


# Global dedicated browser manager singleton
browser_manager = BrowserManager()


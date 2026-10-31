import re
from typing import Dict, Any, Tuple
import httpx

from app.agents.browser_head.ssrf_filter import SSRFEgressFilter


class PlaywrightBrowserWorker:
    """Browser worker that collects public website metadata and content with SSRF egress enforcement."""

    @classmethod
    async def extract_website_intelligence(
        cls,
        target_url: str,
        timeout_seconds: int = 20,
    ) -> Tuple[bytes, Dict[str, Any]]:
        # 1. Enforce SSRF Egress Filter (AC-SEC-02)
        hostname, resolved_ips = SSRFEgressFilter.validate_url(target_url)

        # 2. Fetch page content using secure HTTP client with timeout & limits
        headers = {
            "User-Agent": "ZAPRICA-OSINT-Intelligence-Bot/1.0 (+https://zaprica.local/bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        async with httpx.AsyncClient(
            timeout=float(timeout_seconds),
            follow_redirects=True,
            verify=True,
            max_redirects=5,
        ) as client:
            resp = await client.get(target_url, headers=headers)

            # Re-check redirect URL destination if redirect occurred
            if str(resp.url) != target_url:
                SSRFEgressFilter.validate_url(str(resp.url))

            raw_bytes = resp.content
            html_text = resp.text

        # 3. Parse Metadata & Technical Indicators
        extracted = cls._parse_html_metadata(html_text, dict(resp.headers), str(resp.url))
        extracted["resolved_ips"] = resolved_ips
        extracted["http_status"] = resp.status_code

        return raw_bytes, extracted

    @staticmethod
    def _parse_html_metadata(html_content: str, response_headers: Dict[str, str], current_url: str) -> Dict[str, Any]:
        """Extract title, meta tags, headers, tech stack clues, contacts, and links."""
        metadata: Dict[str, Any] = {
            "url": current_url,
            "title": "",
            "meta_tags": {},
            "tech_stack": [],
            "contacts": [],
            "external_links": [],
            "headings": [],
        }

        # 1. Title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # 2. Server headers (tech stack)
        for h, v in response_headers.items():
            h_low = h.lower()
            if h_low in ["server", "x-powered-by", "x-generator", "via"]:
                metadata["tech_stack"].append({"type": h_low, "value": v})

        # 3. Meta tags
        meta_matches = re.findall(r'<meta\s+([^>]+)>', html_content, re.IGNORECASE)
        for meta in meta_matches:
            name_match = re.search(r'(?:name|property)\s*=\s*["\']([^"\']+)["\']', meta, re.IGNORECASE)
            content_match = re.search(r'content\s*=\s*["\']([^"\']+)["\']', meta, re.IGNORECASE)
            if name_match and content_match:
                name = name_match.group(1).strip()
                content = content_match.group(1).strip()
                metadata["meta_tags"][name] = content
                if name.lower() in ["generator", "author"]:
                    metadata["tech_stack"].append({"type": name.lower(), "value": content})

        # 4. Contacts (emails, tel)
        email_matches = set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html_content))
        for email in email_matches:
            if not email.endswith(".png") and not email.endswith(".jpg"):
                metadata["contacts"].append({"type": "email", "value": email})

        # 5. Headings (h1)
        h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
        for h1 in h1_matches:
            clean_h1 = re.sub(r'<[^>]+>', '', h1).strip()
            if clean_h1:
                metadata["headings"].append(clean_h1)

        # 6. External links
        href_matches = set(re.findall(r'href\s*=\s*["\'](https?://[^"\']+)["\']', html_content, re.IGNORECASE))
        for href in list(href_matches)[:15]:
            metadata["external_links"].append(href)

        return metadata

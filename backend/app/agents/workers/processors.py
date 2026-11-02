import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import Dict, List, Optional, Any, Set, Tuple
import html


class DataCleaner:
    """Deterministic worker that cleans and sanitizes raw web content and text."""

    @staticmethod
    def clean_html_text(raw_html: str) -> str:
        """Strip executable script/style tags, unescape HTML entities, and collapse whitespace."""
        if not raw_html:
            return ""

        # Remove <script> and <style> blocks
        cleaned = re.sub(r"<(script|style|iframe|object|embed)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
        # Remove remaining tags
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        # Decode entities
        cleaned = html.unescape(cleaned)
        # Collapse multiple whitespaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def sanitize_untrusted_snippet(text: str, max_length: int = 1000) -> str:
        """Truncate and clean snippet from untrusted external source."""
        if not text:
            return ""
        # Remove control characters
        cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")
        return cleaned[:max_length].strip()


class DataNormalizer:
    """Deterministic worker that standardizes URLs, domains, emails, and identifiers."""

    TRACKING_PARAMS: Set[str] = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid"
    }

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """Canonicalize URL: lowercase scheme & host, strip tracking query parameters, sort query, strip trailing slash."""
        if not url:
            return ""

        url = url.strip()
        lower_url = url.lower()
        if not lower_url.startswith("http://") and not lower_url.startswith("https://"):
            url = f"https://{url}"

        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Filter out tracking parameters
        query_pairs = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in cls.TRACKING_PARAMS
        ]
        query_pairs.sort()
        query = urlencode(query_pairs)

        # Path normalization: strip trailing slash for non-root paths
        path = parsed.path or "/"
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        return urlunparse((scheme, netloc, path, parsed.params, query, ""))

    @staticmethod
    def normalize_domain(domain: str) -> str:
        """Canonicalize domain name: strip scheme, path, port, www. prefix, and lowercase."""
        if not domain:
            return ""
        d = domain.strip().lower()
        if "://" in d:
            d = d.split("://", 1)[1]
        d = d.split("/", 1)[0].split(":", 1)[0]
        if d.startswith("www."):
            d = d[4:]
        return d

    @staticmethod
    def normalize_email(email: str) -> str:
        """Canonicalize email address: lowercase and strip whitespace."""
        if not email or "@" not in email:
            return ""
        user, domain = email.strip().lower().split("@", 1)
        return f"{user}@{DataNormalizer.normalize_domain(domain)}"

    @staticmethod
    def normalize_tech_stack_name(name: str) -> str:
        """Standardize server and library names."""
        n = name.strip().lower()
        if "nginx" in n:
            return "nginx"
        elif "apache" in n:
            return "apache"
        elif "cloudflare" in n:
            return "cloudflare"
        elif "express" in n:
            return "express"
        elif "react" in n:
            return "react"
        elif "next.js" in n or "nextjs" in n:
            return "next.js"
        return n


class DuplicateDetector:
    """Deterministic worker that detects exact and semantic duplicates among findings."""

    @staticmethod
    def deduplicate(findings: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Deduplicate findings based on (finding_type, normalized_value).
        When duplicates occur, merge their source references rather than dropping evidence.
        Returns (unique_findings, duplicate_count).
        """
        seen: Dict[str, Dict[str, Any]] = {}
        duplicates_count = 0

        for f in findings:
            ftype = f.get("finding_type", "generic")
            nval = f.get("normalized_value") or f.get("title", "")
            key = f"{ftype}:{nval.strip().lower()}"

            if key in seen:
                duplicates_count += 1
                existing = seen[key]
                # Merge sources
                existing_sources = existing.setdefault("sources", [])
                for src in f.get("sources", []):
                    # Check if source already cited
                    if not any(s.get("source_url") == src.get("source_url") for s in existing_sources):
                        existing_sources.append(src)
            else:
                seen[key] = dict(f)

        return list(seen.values()), duplicates_count


class DataClassifier:
    """Deterministic worker that classifies extracted data into structured finding categories."""

    @staticmethod
    def classify(attribute_name: str, value: str) -> str:
        attr = attribute_name.lower().strip()
        if any(k in attr for k in ["server", "tech", "generator", "cms", "framework", "x-powered-by"]):
            return "tech_stack"
        elif any(k in attr for k in ["email", "phone", "contact", "address", "author"]):
            return "contact"
        elif any(k in attr for k in ["ip", "dns", "nameserver", "cname", "mx", "host", "port"]):
            return "network_infrastructure"
        elif any(k in attr for k in ["title", "description", "keywords", "h1", "og:"]):
            return "domain_info"
        elif any(k in attr for k in ["twitter", "github", "linkedin", "social"]):
            return "social_profile"
        return "metadata"


class SortingAndIndexingWorker:
    """Deterministic worker that sorts and indexes extracted findings and artifacts."""

    @staticmethod
    def sort_findings(findings: List[Dict[str, Any]], sort_key: str = "confidence_level", reverse: bool = True) -> List[Dict[str, Any]]:
        """Sorts findings deterministically by confidence or alphabetical title."""
        rank_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        def _key_func(item: Dict[str, Any]):
            if sort_key == "confidence_level":
                conf = item.get("confidence_level", "medium").lower()
                return rank_order.get(conf, 0)
            return str(item.get(sort_key, "")).lower()

        return sorted(findings, key=_key_func, reverse=reverse)

    @staticmethod
    def index_by_type(findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Indexes findings into categories for quick correlation."""
        indexed: Dict[str, List[Dict[str, Any]]] = {}
        for f in findings:
            cat = f.get("finding_type", "generic")
            indexed.setdefault(cat, []).append(f)
        return indexed

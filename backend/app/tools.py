"""OSINT tool implementations - real, functional tools for DNS, HTTP, TLS, WHOIS."""
import hashlib
import json
import socket
import ssl
import struct
from datetime import datetime, timezone
from typing import Any, Optional

import httpx


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── DNS Lookup ───────────────────────────────────────────────────────────────

async def dns_lookup(domain: str, record_type: str = "A") -> dict:
    """Resolve DNS records for a domain using dnspython."""
    import dns.resolver

    record_type = record_type.upper()
    allowed_types = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR", "SRV"}
    if record_type not in allowed_types:
        return {"error": f"Unsupported record type: {record_type}. Allowed: {allowed_types}"}

    try:
        answers = dns.resolver.resolve(domain, record_type)
        records = []
        for rdata in answers:
            records.append(str(rdata))

        result = {
            "tool": "dns_lookup",
            "domain": domain,
            "record_type": record_type,
            "records": records,
            "collected_at": _utcnow(),
        }
        result["sha256"] = _sha256(json.dumps(result, sort_keys=True))
        return result
    except dns.resolver.NXDOMAIN:
        return {"tool": "dns_lookup", "domain": domain, "error": "Domain does not exist (NXDOMAIN)"}
    except dns.resolver.NoAnswer:
        return {"tool": "dns_lookup", "domain": domain, "error": f"No {record_type} records found"}
    except dns.resolver.NoNameservers:
        return {"tool": "dns_lookup", "domain": domain, "error": "No nameservers available"}
    except Exception as e:
        return {"tool": "dns_lookup", "domain": domain, "error": str(e)}


# ─── HTTP Metadata ────────────────────────────────────────────────────────────

async def http_metadata(url: str) -> dict:
    """Collect HTTP response headers and metadata from a URL."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            verify=True,
            headers={"User-Agent": "ZAPRICA-OSINT/1.0 (Authorized Investigation)"}
        ) as client:
            resp = await client.head(url)

            headers_dict = dict(resp.headers)
            result = {
                "tool": "http_metadata",
                "url": str(resp.url),
                "original_url": url,
                "status_code": resp.status_code,
                "headers": headers_dict,
                "server": headers_dict.get("server", "unknown"),
                "content_type": headers_dict.get("content-type", "unknown"),
                "security_headers": {
                    "strict-transport-security": headers_dict.get("strict-transport-security"),
                    "x-content-type-options": headers_dict.get("x-content-type-options"),
                    "x-frame-options": headers_dict.get("x-frame-options"),
                    "content-security-policy": headers_dict.get("content-security-policy"),
                    "x-xss-protection": headers_dict.get("x-xss-protection"),
                },
                "redirect_history": [str(r.url) for r in resp.history],
                "collected_at": _utcnow(),
            }
            result["sha256"] = _sha256(json.dumps(result, sort_keys=True, default=str))
            return result
    except httpx.ConnectTimeout:
        return {"tool": "http_metadata", "url": url, "error": "Connection timed out"}
    except httpx.ConnectError as e:
        return {"tool": "http_metadata", "url": url, "error": f"Connection failed: {str(e)}"}
    except Exception as e:
        return {"tool": "http_metadata", "url": url, "error": str(e)}


# ─── TLS Certificate ─────────────────────────────────────────────────────────

async def tls_certificate_info(hostname: str, port: int = 443) -> dict:
    """Retrieve TLS certificate metadata for a hostname."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()

                subject = dict(x[0] for x in cert.get("subject", ()))
                issuer = dict(x[0] for x in cert.get("issuer", ()))
                san = []
                for ext_type, ext_value in cert.get("subjectAltName", ()):
                    san.append(f"{ext_type}:{ext_value}")

                result = {
                    "tool": "tls_certificate",
                    "hostname": hostname,
                    "port": port,
                    "subject": subject,
                    "issuer": issuer,
                    "serial_number": cert.get("serialNumber"),
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "subject_alt_names": san,
                    "version": cert.get("version"),
                    "cipher_suite": cipher[0] if cipher else None,
                    "protocol": cipher[1] if cipher else None,
                    "collected_at": _utcnow(),
                }
                result["sha256"] = _sha256(json.dumps(result, sort_keys=True, default=str))
                return result
    except socket.timeout:
        return {"tool": "tls_certificate", "hostname": hostname, "error": "Connection timed out"}
    except ssl.SSLCertVerificationError as e:
        return {"tool": "tls_certificate", "hostname": hostname, "error": f"SSL verification failed: {str(e)}"}
    except Exception as e:
        return {"tool": "tls_certificate", "hostname": hostname, "error": str(e)}


# ─── RDAP / WHOIS ────────────────────────────────────────────────────────────

async def rdap_lookup(domain: str) -> dict:
    """Query RDAP for domain registration data (replaces legacy WHOIS)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"https://rdap.org/domain/{domain}")
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "tool": "rdap_lookup",
                    "domain": domain,
                    "status": data.get("status", []),
                    "name": data.get("ldhName"),
                    "handle": data.get("handle"),
                    "nameservers": [
                        ns.get("ldhName") for ns in data.get("nameservers", [])
                    ],
                    "events": [
                        {"action": e.get("eventAction"), "date": e.get("eventDate")}
                        for e in data.get("events", [])
                    ],
                    "entities": [],
                    "collected_at": _utcnow(),
                }
                for entity in data.get("entities", []):
                    roles = entity.get("roles", [])
                    vcard = entity.get("vcardArray", [None, []])
                    e_info = {"roles": roles, "handle": entity.get("handle")}
                    if isinstance(vcard, list) and len(vcard) > 1:
                        for item in vcard[1]:
                            if isinstance(item, list) and len(item) >= 4:
                                if item[0] == "fn":
                                    e_info["name"] = item[3]
                                elif item[0] == "email":
                                    e_info["email"] = item[3]
                    result["entities"].append(e_info)

                result["sha256"] = _sha256(json.dumps(result, sort_keys=True, default=str))
                return result
            elif resp.status_code == 404:
                return {"tool": "rdap_lookup", "domain": domain, "error": "Domain not found in RDAP"}
            else:
                return {"tool": "rdap_lookup", "domain": domain, "error": f"RDAP returned status {resp.status_code}"}
    except Exception as e:
        return {"tool": "rdap_lookup", "domain": domain, "error": str(e)}


# ─── Webpage Metadata ────────────────────────────────────────────────────────

async def webpage_metadata(url: str) -> dict:
    """Extract metadata (title, description, open graph tags) from a webpage."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "ZAPRICA-OSINT/1.0 (Authorized Investigation)"}
        ) as client:
            resp = await client.get(url)
            html = resp.text[:50000]  # Limit to prevent memory issues

            import re
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', html, re.IGNORECASE)
            og_title = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']*)["\']', html, re.IGNORECASE)
            og_desc = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']*)["\']', html, re.IGNORECASE)
            og_image = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']*)["\']', html, re.IGNORECASE)

            # Extract linked domains
            links = re.findall(r'href=["\']https?://([^/"\']+)', html, re.IGNORECASE)
            unique_domains = list(set(links))[:20]

            result = {
                "tool": "webpage_metadata",
                "url": str(resp.url),
                "status_code": resp.status_code,
                "title": title_match.group(1).strip() if title_match else None,
                "description": desc_match.group(1).strip() if desc_match else None,
                "og_title": og_title.group(1).strip() if og_title else None,
                "og_description": og_desc.group(1).strip() if og_desc else None,
                "og_image": og_image.group(1).strip() if og_image else None,
                "linked_domains": unique_domains,
                "content_length": len(html),
                "collected_at": _utcnow(),
            }
            result["sha256"] = _sha256(json.dumps(result, sort_keys=True, default=str))
            return result
    except Exception as e:
        return {"tool": "webpage_metadata", "url": url, "error": str(e)}


# ─── Tool Registry ───────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "dns_lookup": {
        "name": "dns_lookup",
        "description": "Resolve DNS records (A, AAAA, MX, NS, TXT, CNAME, SOA) for a domain",
        "category": "dns",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to look up"},
                "record_type": {"type": "string", "default": "A", "description": "DNS record type"},
            },
            "required": ["domain"],
        },
        "handler": dns_lookup,
        "requires_network": True,
        "risk_level": "low",
    },
    "http_metadata": {
        "name": "http_metadata",
        "description": "Collect HTTP response headers and security header analysis",
        "category": "web",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL or domain to inspect"},
            },
            "required": ["url"],
        },
        "handler": http_metadata,
        "requires_network": True,
        "risk_level": "low",
    },
    "tls_certificate": {
        "name": "tls_certificate",
        "description": "Retrieve and analyze TLS/SSL certificate metadata",
        "category": "crypto",
        "input_schema": {
            "type": "object",
            "properties": {
                "hostname": {"type": "string", "description": "Hostname to inspect"},
                "port": {"type": "integer", "default": 443},
            },
            "required": ["hostname"],
        },
        "handler": tls_certificate_info,
        "requires_network": True,
        "risk_level": "low",
    },
    "rdap_lookup": {
        "name": "rdap_lookup",
        "description": "Query RDAP for domain registration data (registrar, nameservers, contacts)",
        "category": "registration",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to query"},
            },
            "required": ["domain"],
        },
        "handler": rdap_lookup,
        "requires_network": True,
        "risk_level": "low",
    },
    "webpage_metadata": {
        "name": "webpage_metadata",
        "description": "Extract page title, description, Open Graph tags, and linked domains",
        "category": "web",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to extract metadata from"},
            },
            "required": ["url"],
        },
        "handler": webpage_metadata,
        "requires_network": True,
        "risk_level": "low",
    },
}


async def execute_tool(tool_name: str, parameters: dict) -> dict:
    """Execute a registered tool by name with given parameters."""
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {tool_name}", "available_tools": list(TOOL_REGISTRY.keys())}

    tool = TOOL_REGISTRY[tool_name]
    handler = tool["handler"]

    try:
        result = await handler(**parameters)
        return result
    except TypeError as e:
        return {"error": f"Invalid parameters for {tool_name}: {str(e)}"}
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

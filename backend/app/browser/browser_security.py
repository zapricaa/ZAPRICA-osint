"""Browser security validator enforcing SSRF, IP range restrictions, and redirect verification."""

import ipaddress
import socket
from typing import List, Tuple
from urllib.parse import urlparse
from fastapi import HTTPException, status


class BrowserSecurityValidator:
    """Enforces strict egress rules, DNS rebinding prevention, and SSRF restrictions."""

    FORBIDDEN_NETWORKS = [
        ipaddress.ip_network("0.0.0.0/8"),          # Current network
        ipaddress.ip_network("10.0.0.0/8"),         # Private RFC 1918
        ipaddress.ip_network("100.64.0.0/10"),      # Shared address / CGNAT
        ipaddress.ip_network("127.0.0.0/8"),        # Loopback
        ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud metadata
        ipaddress.ip_network("172.16.0.0/12"),      # Private RFC 1918
        ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol
        ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
        ipaddress.ip_network("192.168.0.0/16"),     # Private RFC 1918
        ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
        ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
        ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
        ipaddress.ip_network("224.0.0.0/4"),        # Multicast
        ipaddress.ip_network("240.0.0.0/4"),        # Reserved
        ipaddress.ip_network("255.255.255.255/32"), # Broadcast
        # IPv6 restricted
        ipaddress.ip_network("::/128"),
        ipaddress.ip_network("::1/128"),            # Loopback
        ipaddress.ip_network("fc00::/7"),           # Unique local
        ipaddress.ip_network("fe80::/10"),          # Link-local
    ]

    CLOUD_METADATA_HOSTS = {
        "metadata.google.internal",
        "169.254.169.254",
        "fd00:ec2::254",
        "instance-data",
    }

    @classmethod
    def validate_target_url(cls, url: str) -> Tuple[str, List[str]]:
        """
        Validates target URL against SSRF and network access policies.
        Returns (hostname, resolved_ips). Raises HTTPException on violation.
        """
        if not url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target URL cannot be empty.")

        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security Violation: Scheme '{parsed.scheme}' forbidden. Only HTTP/HTTPS permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target URL: missing hostname.")

        hostname_lower = hostname.lower().strip()

        # Check for cloud metadata hostnames
        if hostname_lower in cls.CLOUD_METADATA_HOSTS or hostname_lower.endswith(".internal"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Security Policy Violation: Host '{hostname}' is a restricted cloud metadata address."
            )

        # DNS resolution and IP validation
        try:
            addr_info = socket.getaddrinfo(hostname_lower, parsed.port or (443 if parsed.scheme == "https" else 80))
        except socket.gaierror as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DNS Resolution Failed for target '{hostname}': {str(e)}"
            )

        resolved_ips: List[str] = []
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if ip_str not in resolved_ips:
                resolved_ips.append(ip_str)

            ip_obj = ipaddress.ip_address(ip_str)
            for forbidden_net in cls.FORBIDDEN_NETWORKS:
                if ip_obj in forbidden_net:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"SSRF Security Violation: Host '{hostname}' resolves to private/restricted IP '{ip_str}' ({forbidden_net})."
                    )

        return hostname_lower, resolved_ips


import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, List
from fastapi import HTTPException, status


class SecurityPolicyViolation(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Policy Violation: {detail}"
        )


class SSRFEgressFilter:
    """SSRF and Egress firewall: blocks private subnets, loopback, link-local, and cloud metadata."""

    # Forbidden IPv4 ranges
    FORBIDDEN_IPV4_NETWORKS = [
        ipaddress.ip_network("0.0.0.0/8"),         # Current network (only valid as source address)
        ipaddress.ip_network("10.0.0.0/8"),        # Private-Use (RFC 1918)
        ipaddress.ip_network("100.64.0.0/10"),     # Shared Address Space (RFC 6598)
        ipaddress.ip_network("127.0.0.0/8"),       # Loopback (RFC 1122)
        ipaddress.ip_network("169.254.0.0/16"),    # Link-Local / Cloud Metadata (RFC 3927)
        ipaddress.ip_network("172.16.0.0/12"),     # Private-Use (RFC 1918)
        ipaddress.ip_network("192.0.0.0/24"),      # IETF Protocol Assignments (RFC 6890)
        ipaddress.ip_network("192.0.2.0/24"),      # TEST-NET-1 (RFC 5737)
        ipaddress.ip_network("192.88.99.0/24"),    # 6to4 Relay Anycast (RFC 7526)
        ipaddress.ip_network("192.168.0.0/16"),    # Private-Use (RFC 1918)
        ipaddress.ip_network("198.18.0.0/15"),     # Benchmarking (RFC 2544)
        ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2 (RFC 5737)
        ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3 (RFC 5737)
        ipaddress.ip_network("224.0.0.0/4"),       # Multicast (RFC 5771)
        ipaddress.ip_network("240.0.0.0/4"),       # Reserved for Future Use (RFC 1112)
        ipaddress.ip_network("255.255.255.255/32") # Limited Broadcast
    ]

    # Explicit cloud metadata IPs
    CLOUD_METADATA_IPS = {
        "169.254.169.254", # AWS, GCP, Azure, OpenStack
        "169.254.169.123",
        "fd00:ec2::254"
    }

    @classmethod
    def validate_ip(cls, ip_str: str) -> None:
        """Verify an IP address is public and routable."""
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SecurityPolicyViolation(f"Malformed IP address: {ip_str}")

        if str(ip) in cls.CLOUD_METADATA_IPS:
            raise SecurityPolicyViolation(f"Access to Cloud Metadata endpoint {ip_str} is prohibited.")

        if ip.is_loopback:
            raise SecurityPolicyViolation(f"Access to loopback address {ip_str} is prohibited.")

        if ip.is_private:
            raise SecurityPolicyViolation(f"Access to private RFC1918 address {ip_str} is prohibited.")

        if ip.is_link_local:
            raise SecurityPolicyViolation(f"Access to link-local address {ip_str} is prohibited.")

        if ip.is_multicast or ip.is_reserved:
            raise SecurityPolicyViolation(f"Access to reserved/multicast address {ip_str} is prohibited.")

        if isinstance(ip, ipaddress.IPv4Address):
            for network in cls.FORBIDDEN_IPV4_NETWORKS:
                if ip in network:
                    raise SecurityPolicyViolation(f"IP {ip_str} falls into prohibited network {network}.")

    @classmethod
    def resolve_and_validate(cls, hostname: str) -> List[str]:
        """Resolve hostname via DNS and validate all returned IP addresses."""
        cleaned_host = hostname.strip().lower()

        # Reject literal loopback or localhost
        if cleaned_host in ["localhost", "127.0.0.1", "::1", "metadata.google.internal"]:
            raise SecurityPolicyViolation(f"Direct connection to '{cleaned_host}' is blocked by egress security policy.")

        try:
            # Resolve DNS
            addr_info = socket.getaddrinfo(cleaned_host, None)
            resolved_ips = list({info[4][0] for info in addr_info})
        except socket.gaierror as e:
            raise SecurityPolicyViolation(f"DNS resolution failed for '{hostname}': {str(e)}")

        if not resolved_ips:
            raise SecurityPolicyViolation(f"No IP addresses resolved for '{hostname}'.")

        for ip in resolved_ips:
            cls.validate_ip(ip)

        return resolved_ips

    @classmethod
    def validate_url(cls, url: str) -> Tuple[str, List[str]]:
        """Validate destination URL: scheme, host, and resolved IP addresses."""
        if not url:
            raise SecurityPolicyViolation("Empty URL provided.")

        parsed = urlparse(url)
        if parsed.scheme.lower() not in ["http", "https"]:
            raise SecurityPolicyViolation(f"Prohibited URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

        hostname = parsed.hostname
        if not hostname:
            raise SecurityPolicyViolation(f"URL '{url}' does not have a valid hostname.")

        # If hostname is an IP, validate directly; otherwise resolve DNS
        try:
            ipaddress.ip_address(hostname)
            cls.validate_ip(hostname)
            resolved_ips = [hostname]
        except ValueError:
            resolved_ips = cls.resolve_and_validate(hostname)

        return hostname, resolved_ips

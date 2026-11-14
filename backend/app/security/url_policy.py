"""Outbound URL policy for agent tools (browser navigation, read_url).

Only public http(s) destinations are allowed. Hostnames are resolved and every
resolved address must be public, so a DNS name pointing at 127.0.0.1 or a cloud
metadata IP is rejected too.
"""
import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "metadata"}


class UrlPolicyError(ValueError):
    pass


_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    # DNS64 resolvers (common on IPv6-only and mobile networks) return NAT64 addresses that wrap
    # the real IPv4; IPv4-mapped IPv6 does the same. Judge the embedded IPv4, not the wrapper.
    if isinstance(addr, ipaddress.IPv6Address):
        if addr in _NAT64:
            addr = ipaddress.IPv4Address(int(addr) & 0xFFFFFFFF)
        elif addr.ipv4_mapped is not None:
            addr = addr.ipv4_mapped
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


async def check_url(url: str) -> str:
    """Return the normalized URL, or raise UrlPolicyError explaining why it is blocked."""
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UrlPolicyError(f"Only http and https URLs are allowed (got '{parsed.scheme or 'none'}:').")
    host = (parsed.hostname or "").lower()
    if not host:
        raise UrlPolicyError("URL has no host.")
    if host in _BLOCKED_HOSTNAMES or host.endswith(".localhost") or host.endswith(".internal"):
        raise UrlPolicyError(f"Host '{host}' is not allowed.")

    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise UrlPolicyError(f"Could not resolve host '{host}'.")
        addresses = sorted({info[4][0] for info in infos})

    for ip in addresses:
        if not _is_public(ip.split("%")[0]):
            raise UrlPolicyError(f"Host '{host}' resolves to a non-public address.")
    return parsed.geturl()

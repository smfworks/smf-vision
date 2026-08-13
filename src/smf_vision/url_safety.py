"""URL validation for camera fetches and webhook dispatch.

LAN cameras need RFC1918, so private HTTP(S) is allowed for *sources*.
Webhooks default to public HTTPS only. Metadata and non-http(s) schemes
are always rejected.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

METADATA_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
    }
)
METADATA_NETWORKS = (
    ipaddress.ip_network("169.254.169.254/32"),
    ipaddress.ip_network("169.254.170.2/32"),
    ipaddress.ip_network("fd00:ec2::254/128"),
)
LINK_LOCAL = ipaddress.ip_network("169.254.0.0/16")
LINK_LOCAL_V6 = ipaddress.ip_network("fe80::/10")


class UnsafeURLError(ValueError):
    """Raised when a URL is not allowed for the requested role."""


def _host_ips(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    if host.lower() in METADATA_HOSTS:
        raise UnsafeURLError(f"metadata hostname is not allowed: {host}")
    try:
        return [ipaddress.ip_address(host.strip("[]"))]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"cannot resolve host {host!r}: {exc}") from exc
    addrs: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        raw = info[4][0]
        parsed_ip = ipaddress.ip_address(raw)
        if isinstance(parsed_ip, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            addrs.append(parsed_ip)
    if not addrs:
        raise UnsafeURLError(f"no addresses for host {host!r}")
    return addrs


def _is_metadata(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(ip in net for net in METADATA_NETWORKS)


def _is_private(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip in LINK_LOCAL
        or ip in LINK_LOCAL_V6
    )


def validate_http_url(
    url: str,
    *,
    role: str,
    allow_private: bool,
    require_https: bool,
) -> str:
    """Return the URL if it is safe for *role*, else raise UnsafeURLError."""
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError(f"{role} URL is required")
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise UnsafeURLError(f"{role} URL must be http(s), got {scheme or 'missing scheme'!r}")
    if require_https and scheme != "https":
        raise UnsafeURLError(f"{role} URL must be https")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError(f"{role} URL is missing a hostname")
    if host.lower() in METADATA_HOSTS:
        raise UnsafeURLError(f"{role} URL points at a metadata host")
    for ip in _host_ips(host):
        if _is_metadata(ip):
            raise UnsafeURLError(f"{role} URL resolves to a metadata address: {ip}")
        if _is_private(ip) and not allow_private:
            raise UnsafeURLError(f"{role} URL resolves to a non-public address: {ip}")
    return url.strip()


def validate_camera_source(source: str) -> str:
    """Validate a camera source. Numeric indices and local paths are left alone."""
    if source.startswith(("http://", "https://")):
        return validate_http_url(source, role="camera", allow_private=True, require_https=False)
    if "://" in source and not source.startswith("rtsp://"):
        raise UnsafeURLError(f"unsupported camera source scheme: {source.split('://', 1)[0]}")
    return source


def validate_webhook_url(url: str, *, allow_insecure: bool = False, allow_private: bool = False) -> str:
    return validate_http_url(
        url,
        role="webhook",
        allow_private=allow_private,
        require_https=not allow_insecure,
    )

"""Check-in route implementation helpers."""

from __future__ import annotations


def extract_ip_address(request) -> str:
    """Extract client IP from request, respecting x-forwarded-for header."""
    ip_address = ""
    if request:
        forwarded = request.headers.get("x-forwarded-for", "")
        ip_address = (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.client.host
            if request.client
            else ""
        )
    return ip_address

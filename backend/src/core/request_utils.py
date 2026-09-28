"""
Helpers to extract client context from a FastAPI `Request`.

Both helpers are side-effect free and never raise: if the request has
no client information attached (e.g. `TestClient` without a proper
scope), they fall back to the string `"unknown"`. This lets callers
log and forward the value without extra null checks.
"""

from fastapi import Request

from src.core.logger import get_logger

logger = get_logger(__name__)


def get_client_ip(request: Request) -> str:
    """Return the client IP, honoring proxy headers when present.

    When the app runs behind a reverse proxy, the connection IP is the
    proxy's, not the client's. This function reads the standard
    forwarding headers in order of trust:

    1. `X-Forwarded-For` — comma-separated list; the first entry is the
       original client, the rest are intermediate proxies.
    2. `X-Real-IP` — a single IP set by some proxies.
    3. `request.client.host` — the raw TCP peer address.

    Falls back to `"unknown"` if the request has no client attached.

    Args:
        request: Incoming FastAPI request.

    Returns:
        Client IP as a string, or `"unknown"` if none could be resolved.
    """
    if not request.client:
        logger.debug("CLIENT_IP_UNAVAILABLE")
        return "unknown"

    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
        logger.debug("CLIENT_IP_EXTRACTED", source="x-forwarded-for", ip=ip)
        return ip

    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        logger.debug("CLIENT_IP_EXTRACTED", source="x-real-ip", ip=x_real_ip)
        return x_real_ip

    ip = request.client.host
    logger.debug("CLIENT_IP_EXTRACTED", source="direct", ip=ip)
    return ip


def get_user_agent(request: Request) -> str:
    """Return the `User-Agent` header, truncated to 500 characters.

    The truncation matches a typical `VARCHAR(500)` column so the value
    can be stored without an extra length check. The full value is only
    available in debug logs, never persisted.

    Args:
        request: Incoming FastAPI request.

    Returns:
        The user agent string, truncated to 500 characters. `"unknown"`
        if the header is missing.
    """
    ua = request.headers.get("user-agent", "unknown")
    truncated_ua = ua[:500]

    if len(ua) > 500:
        logger.debug("USER_AGENT_TRUNCATED", original_length=len(ua), limit=500)

    logger.debug("USER_AGENT_EXTRACTED", length=len(truncated_ua))
    return truncated_ua
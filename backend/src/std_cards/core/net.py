from fastapi import Request


def client_ip(request: Request) -> str | None:
    """Real client IP as resolved by uvicorn's ProxyHeadersMiddleware.

    uvicorn runs with --proxy-headers --forwarded-allow-ips=<pod CIDRs>, so it
    walks X-Forwarded-For right-to-left, skipping trusted proxy hops, and sets
    request.client to the real client. Reading the raw X-Forwarded-For header
    instead would trust the attacker-controlled leftmost entry and let per-IP
    rate limits and the 404 burst lockout be bypassed by rotating the header.
    """
    return request.client.host if request.client else None

from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """Best-effort client IP for rate limiting.

    The app runs behind a reverse proxy, so the real client address is in the
    first hop of ``X-Forwarded-For``. Fall back to the direct socket address
    when the header is missing (e.g. local development).
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Format: "client, proxy1, proxy2" — the client is the first entry.
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None

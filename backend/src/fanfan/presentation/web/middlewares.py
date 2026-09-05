import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.exceptions import HTTP_ERROR_CODE
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ErrorMessage

# An HTTP middleware as registered via `app.middleware("http")`.
HttpMiddleware = Callable[
    [Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]
]

# Standard header used by proxies/clients to carry a request id; we reuse it
# when present so logs can be correlated across services, and generate one
# otherwise.
_REQUEST_ID_HEADER = "X-Request-ID"

# Matches the reverse proxy's own cap (Caddyfile.example's request_body
# max_size). Generous: the largest legitimate body today is a schedule
# spreadsheet, capped at 5MB in the import route itself.
_MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024


def refresh_session_cookie(web_config: WebConfig) -> HttpMiddleware:
    """Re-set the session cookie when a handler renewed the session id.

    Built as a factory because the middleware needs the request-independent
    `WebConfig` (cookie flags / TTL); everything else here is config-free.
    """

    async def middleware(request: Request, call_next) -> Response:
        response = await call_next(request)
        session_id: str | None = getattr(request.state, "renew_session_id", None)
        if session_id:
            set_auth_cookie(response, session_id, web_config)
        return response

    return middleware


async def security_headers(request: Request, call_next) -> Response:
    """Stamp hardening headers on every response.

    Defence-in-depth that travels with the app: even deployed behind a proxy
    that forgets to add them (or exposed directly), the API and its framable
    HTML surfaces — FastAPI's ``/docs`` and the OAuth redirect responses —
    carry the same protection. Values follow the OWASP Secure Headers Project
    (https://owasp.org/www-project-secure-headers/):

    * ``nosniff`` stops MIME-type confusion, which matters for JSON as much as
      for the served docs page.
    * ``X-Frame-Options`` and the modern ``frame-ancestors`` together forbid
      framing (clickjacking) on old and new browsers; only ``frame-ancestors``
      is set — not a full CSP — so Swagger UI's CDN-loaded assets still load.
    * ``strict-origin-when-cross-origin`` keeps the path/query out of the
      ``Referer`` sent to other origins.

    HSTS is deliberately absent: it must be emitted only over HTTPS by the
    TLS-terminating proxy, which the app cannot detect from behind it.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


async def no_store_cache_control(request: Request, call_next) -> Response:
    """Default-deny HTTP caching for the whole API.

    Responses are per-user and dynamic, and the browser must never persist
    them: with no ``Cache-Control`` the browser applies heuristic caching and
    replays stale "online-only" data offline (e.g. a network-only staff feed)
    from its disk cache. ``setdefault`` leaves any explicit ``Cache-Control`` a
    route sets for itself, so a future public, identity-independent GET can opt
    into caching.
    """
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    return response


async def limit_request_body_size(request: Request, call_next) -> Response:
    """Reject a body that declares itself oversized, before anything reads it.

    Defence-in-depth that travels with the app (see `security_headers`): the
    normal hard backstop against a hostile multi-hundred-MB upload is the
    reverse proxy's own `request_body` cap (Caddyfile.example), documented as
    required for the schedule-import endpoint. A deployment that skips or
    misconfigures that proxy setting would otherwise let FastAPI spool the
    whole body into memory before any route or exception handler runs — this
    catches that case from a `Content-Length` a client sent honestly. A
    chunked body with no `Content-Length` still reaches the route unbounded;
    the proxy cap remains the only defence against that.
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            declared_size = None
        if declared_size is not None and declared_size > _MAX_REQUEST_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content=ErrorMessage(
                    code=HTTP_ERROR_CODE, details={"status_code": 413}
                ).model_dump(),
            )

    return await call_next(request)


async def bind_request_context(request: Request, call_next) -> Response:
    """Bind a per-request id into structlog contextvars.

    The logging setup includes ``merge_contextvars`` in its processor chain,
    so every log line emitted while handling this request automatically
    carries the same ``request_id``. This makes it possible to follow a single
    request across all the log lines it produces. The id is echoed back in the
    response header so clients and proxies can reference it too.
    """
    structlog.contextvars.clear_contextvars()
    request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)

    response.headers[_REQUEST_ID_HEADER] = request_id
    return response

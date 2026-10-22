"""HTTP middleware for the web app, written as pure ASGI classes.

Pure ASGI rather than `app.middleware("http")` (BaseHTTPMiddleware): every
request passes through the whole stack, SSE streams included, and
BaseHTTPMiddleware wraps each layer in its own task and memory streams while
also cutting contextvar propagation for whatever sits around it
(https://starlette.dev/middleware/#limitations). Each class leaves non-HTTP
scopes (lifespan) untouched.
"""

import re
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.exceptions import (
    HTTP_ERROR_CODE,
    internal_error_response,
)
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ErrorMessage

# Standard header used by proxies/clients to carry a request id; we reuse it
# when present so logs can be correlated across services, and generate one
# otherwise.
_REQUEST_ID_HEADER = "X-Request-ID"

# Any client can send the header, and its value lands in every log line of the
# request (CWE-117), so a reused id must look like one: room for a UUID or a
# proxy's own format, nothing that could pose as another field or record.
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,128}")

# Matches the reverse proxy's own cap (Caddyfile.example's request_body
# max_size). Generous: the largest legitimate body today is a schedule
# spreadsheet, capped at 5MB in the import route itself.
_MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024


class RefreshSessionCookieMiddleware:
    """Re-set the session cookie when a handler renewed the session id.

    Takes the request-independent `WebConfig` (cookie flags / TTL); everything
    else here is config-free.
    """

    def __init__(self, app: ASGIApp, web_config: WebConfig) -> None:
        self.app = app
        self.web_config = web_config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_cookie(message: Message) -> None:
            if message["type"] == "http.response.start":
                # `request.state` is a view over scope["state"], so the flag a
                # handler set (WebIdProvider) is visible here.
                session_id = scope.get("state", {}).get("renew_session_id")
                if session_id:
                    # Render the cookie through set_auth_cookie on a scratch
                    # Response so its flags stay defined in one place.
                    carrier = Response()
                    set_auth_cookie(carrier, session_id, self.web_config)
                    headers = MutableHeaders(scope=message)
                    for name, value in carrier.raw_headers:
                        if name == b"set-cookie":
                            headers.append("set-cookie", value.decode("latin-1"))
            await send(message)

        await self.app(scope, receive, send_with_cookie)


class CatchUnexpectedErrorsMiddleware:
    """Turn an unanticipated route error into the generic 500 inside the stack.

    An `Exception` handler would do the same, but Starlette runs it in
    `ServerErrorMiddleware` — outermost, after every other middleware has
    unwound — so that 500 lacks CORS (a cross-origin browser sees a network
    error instead), `X-Request-ID`, `Cache-Control` and the security headers.
    Catching here, inside all of them, lets the error response pass back through
    them like any other. Starlette also re-raises from there ("We always
    continue to raise the exception", starlette/middleware/errors.py), so the
    server logged the traceback a second time.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception as exc:
            # Once headers are on the wire (a stream that failed midway) a 500
            # can no longer be sent; let the server close the connection.
            if response_started:
                raise
            await internal_error_response(exc)(scope, receive, send)


class SecurityHeadersMiddleware:
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

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Content-Security-Policy"] = "frame-ancestors 'none'"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            await send(message)

        await self.app(scope, receive, send_with_headers)


class NoStoreCacheControlMiddleware:
    """Default-deny HTTP caching for the whole API.

    Responses are per-user and dynamic, and the browser must never persist
    them: with no ``Cache-Control`` the browser applies heuristic caching and
    replays stale "online-only" data offline (e.g. a network-only staff feed)
    from its disk cache. ``setdefault`` leaves any explicit ``Cache-Control`` a
    route sets for itself, so a future public, identity-independent GET can opt
    into caching.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_cache_control(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).setdefault("Cache-Control", "no-store")
            await send(message)

        await self.app(scope, receive, send_with_cache_control)


class LimitRequestBodySizeMiddleware:
    """Reject a body that declares itself oversized, before anything reads it.

    Defence-in-depth that travels with the app (see `SecurityHeadersMiddleware`):
    the normal hard backstop against a hostile multi-hundred-MB upload is the
    reverse proxy's own `request_body` cap (Caddyfile.example), documented as
    required for the schedule-import endpoint. A deployment that skips or
    misconfigures that proxy setting would otherwise let FastAPI spool the
    whole body into memory before any route or exception handler runs — this
    catches that case from a `Content-Length` a client sent honestly. A
    chunked body with no `Content-Length` still reaches the route unbounded;
    the proxy cap remains the only defence against that.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None
            if declared_size is not None and declared_size > _MAX_REQUEST_BODY_BYTES:
                response = JSONResponse(
                    status_code=413,
                    content=ErrorMessage(
                        code=HTTP_ERROR_CODE, details={"status_code": 413}
                    ).model_dump(),
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


class BindRequestContextMiddleware:
    """Bind a per-request id into structlog contextvars.

    The logging setup includes ``merge_contextvars`` in its processor chain,
    so every log line emitted while handling this request carries the same
    ``request_id``. The id is echoed back in the response header so clients and
    proxies can reference it too.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        structlog.contextvars.clear_contextvars()
        request_id = Headers(scope=scope).get(_REQUEST_ID_HEADER)
        if request_id is None or not _REQUEST_ID_PATTERN.fullmatch(request_id):
            request_id = uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[_REQUEST_ID_HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)

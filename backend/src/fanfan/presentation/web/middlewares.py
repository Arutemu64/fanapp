import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.requests import Request
from starlette.responses import Response

from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie

# An HTTP middleware as registered via `app.middleware("http")`.
HttpMiddleware = Callable[
    [Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]
]

# Standard header used by proxies/clients to carry a request id; we reuse it
# when present so logs can be correlated across services, and generate one
# otherwise.
_REQUEST_ID_HEADER = "X-Request-ID"


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

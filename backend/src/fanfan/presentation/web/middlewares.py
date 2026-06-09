import uuid

import structlog
from starlette.requests import Request
from starlette.responses import Response

# Standard header used by proxies/clients to carry a request id; we reuse it
# when present so logs can be correlated across services, and generate one
# otherwise.
_REQUEST_ID_HEADER = "X-Request-ID"


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

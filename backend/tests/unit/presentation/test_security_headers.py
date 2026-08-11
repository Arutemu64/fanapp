import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from fanfan.presentation.web.middlewares import security_headers

pytestmark = pytest.mark.unit


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "headers": []})


async def _call_next(_: Request) -> Response:
    return PlainTextResponse("ok")


async def test_security_headers_are_set() -> None:
    response = await security_headers(_request(), _call_next)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


async def test_hsts_is_left_to_the_tls_terminator() -> None:
    # The app is behind a TLS-terminating proxy and cannot tell HTTPS from HTTP,
    # so it must never emit HSTS itself.
    response = await security_headers(_request(), _call_next)

    assert "Strict-Transport-Security" not in response.headers

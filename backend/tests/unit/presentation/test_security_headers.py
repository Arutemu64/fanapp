import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from fanfan.presentation.web.middlewares import SecurityHeadersMiddleware

pytestmark = pytest.mark.unit


def _client() -> TestClient:
    app = Starlette(routes=[Route("/", lambda _: PlainTextResponse("ok"))])
    app.add_middleware(SecurityHeadersMiddleware)
    return TestClient(app)


def test_security_headers_are_set() -> None:
    response = _client().get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_hsts_is_left_to_the_tls_terminator() -> None:
    # The app is behind a TLS-terminating proxy and cannot tell HTTPS from HTTP,
    # so it must never emit HSTS itself.
    response = _client().get("/")

    assert "Strict-Transport-Security" not in response.headers

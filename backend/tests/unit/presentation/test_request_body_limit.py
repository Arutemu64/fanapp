import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from fanfan.presentation.web.middlewares import (
    _MAX_REQUEST_BODY_BYTES,
    LimitRequestBodySizeMiddleware,
)

pytestmark = pytest.mark.unit


def _client() -> TestClient:
    # The route never reads the body, so a declared Content-Length is all the
    # middleware sees — no need to send that many bytes.
    app = Starlette(
        routes=[Route("/", lambda _: PlainTextResponse("ok"), methods=["POST"])]
    )
    app.add_middleware(LimitRequestBodySizeMiddleware)
    return TestClient(app)


def test_passes_through_a_body_within_the_limit() -> None:
    response = _client().post(
        "/", headers={"content-length": str(_MAX_REQUEST_BODY_BYTES)}
    )

    assert response.text == "ok"


def test_passes_through_when_content_length_is_absent() -> None:
    # A chunked body with no Content-Length reaches the route unbounded; the
    # reverse proxy's own cap is the only defence against that case.
    response = _client().post("/")

    assert response.text == "ok"


def test_rejects_a_body_over_the_limit() -> None:
    response = _client().post(
        "/", headers={"content-length": str(_MAX_REQUEST_BODY_BYTES + 1)}
    )

    assert response.status_code == 413


def test_passes_through_a_malformed_content_length() -> None:
    response = _client().post("/", headers={"content-length": "not-a-number"})

    assert response.text == "ok"

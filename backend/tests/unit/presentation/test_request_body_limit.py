import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from fanfan.presentation.web.middlewares import (
    _MAX_REQUEST_BODY_BYTES,
    limit_request_body_size,
)

pytestmark = pytest.mark.unit


def _request(content_length: str | None) -> Request:
    headers = [(b"content-length", content_length.encode())] if content_length else []
    return Request({"type": "http", "method": "POST", "headers": headers})


async def _call_next(_: Request) -> Response:
    return PlainTextResponse("ok")


async def test_passes_through_a_body_within_the_limit() -> None:
    response = await limit_request_body_size(
        _request(str(_MAX_REQUEST_BODY_BYTES)), _call_next
    )

    assert response.body == b"ok"


async def test_passes_through_when_content_length_is_absent() -> None:
    # A chunked body with no Content-Length reaches the route unbounded; the
    # reverse proxy's own cap is the only defence against that case.
    response = await limit_request_body_size(_request(None), _call_next)

    assert response.body == b"ok"


async def test_rejects_a_body_over_the_limit() -> None:
    response = await limit_request_body_size(
        _request(str(_MAX_REQUEST_BODY_BYTES + 1)), _call_next
    )

    assert response.status_code == 413


async def test_passes_through_a_malformed_content_length() -> None:
    response = await limit_request_body_size(_request("not-a-number"), _call_next)

    assert response.body == b"ok"

import pytest
from starlette.requests import Request

from fanfan.presentation.web.responses import resource_location

pytestmark = pytest.mark.unit


def _request(root_path: str) -> Request:
    return Request({"type": "http", "root_path": root_path, "headers": []})


def test_location_keeps_the_api_prefix_the_proxy_strips() -> None:
    assert resource_location(_request("/api"), "/voting/votes/1") == (
        "/api/voting/votes/1"
    )


def test_location_without_a_root_path_is_the_route_path() -> None:
    assert resource_location(_request(""), "/sync/sources") == "/sync/sources"

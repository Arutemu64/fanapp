import pytest
from pydantic import HttpUrl, SecretStr
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.middlewares import RefreshSessionCookieMiddleware
from fanfan.presentation.web.routes.auth.cookies import SESSION_COOKIE_NAME

pytestmark = pytest.mark.unit


def _renewing(request: Request) -> Response:
    # What WebIdProvider does when the session store reports a touched session.
    request.state.renew_session_id = "renewed-session"
    return PlainTextResponse("ok")


def _client() -> TestClient:
    app = Starlette(
        routes=[
            Route("/renew", _renewing),
            Route("/plain", lambda _: PlainTextResponse("ok")),
        ]
    )
    web_config = WebConfig(
        host="localhost",
        port=8000,
        public_url=HttpUrl("http://localhost:3000/"),
        secret_key=SecretStr("test-secret-key"),
    )
    app.add_middleware(RefreshSessionCookieMiddleware, web_config=web_config)
    return TestClient(app)


def test_renewed_session_re_sets_the_cookie() -> None:
    response = _client().get("/renew")

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE_NAME}=renewed-session")
    assert "HttpOnly" in cookie


def test_untouched_session_sets_no_cookie() -> None:
    response = _client().get("/plain")

    assert "set-cookie" not in response.headers

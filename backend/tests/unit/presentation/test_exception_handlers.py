import logging

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.testclient import TestClient

from fanfan.core.exceptions.auth import IncorrectPassword
from fanfan.core.exceptions.base import NotFound
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.presentation.web.exceptions import (
    add_exception_handlers,
    is_expected_error,
)
from fanfan.presentation.web.exceptions import logger as handlers_logger
from fanfan.presentation.web.middlewares import (
    bind_request_context,
    catch_unexpected_errors,
    no_store_cache_control,
)

pytestmark = pytest.mark.unit


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError

    @app.get("/unmarked")
    async def unmarked() -> None:
        # Internal-only: meant to be re-raised as a flow-specific RateLimited.
        raise CooldownActive(retry_after=30)

    @app.post("/password")
    async def change_password() -> None:
        raise IncorrectPassword

    # The same relative order as create_app: the catch sits inside the
    # middleware whose headers every response must carry.
    app.middleware("http")(catch_unexpected_errors)
    app.middleware("http")(no_store_cache_control)
    app.middleware("http")(bind_request_context)
    add_exception_handlers(app)
    return app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # A migration test elsewhere runs Alembic's fileConfig() in-process, which
    # disables every logger created before it (disable_existing_loggers=True).
    monkeypatch.setattr(handlers_logger, "disabled", False)
    return TestClient(_app(), raise_server_exceptions=False)


def test_unexpected_error_keeps_the_middleware_headers(client: TestClient) -> None:
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_ERROR", "details": {}}
    assert response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "no-store"


def test_unexpected_error_is_logged(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        client.get("/boom")

    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], RuntimeError)


def test_unmarked_domain_exception_does_not_leak(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        response = client.get("/unmarked")

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_ERROR", "details": {}}
    assert any(r.levelno == logging.ERROR for r in caplog.records)


@pytest.mark.parametrize(
    ("method", "status_code"),
    [("GET", 404), ("POST", 405)],
)
def test_router_errors_use_the_error_shape(
    client: TestClient, method: str, status_code: int
) -> None:
    path = "/missing" if status_code == 404 else "/boom"

    response = client.request(method, path)

    assert response.status_code == status_code
    assert response.json() == {
        "code": "HTTP_ERROR",
        "details": {"status_code": status_code},
    }


def test_incorrect_password_is_bad_input_not_a_lost_session(
    client: TestClient,
) -> None:
    # A 401 would make the frontend treat the session as ended.
    response = client.post("/password")

    assert response.status_code == 400
    assert response.json()["code"] == "INCORRECT_PASSWORD"


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (NotFound(), True),
        (RequestValidationError([]), True),
        (CooldownActive(retry_after=30), False),
        (RuntimeError(), False),
    ],
)
def test_is_expected_error(exc: BaseException, *, expected: bool) -> None:
    assert is_expected_error(exc) is expected

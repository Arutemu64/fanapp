import logging
from http import HTTPStatus
from typing import Annotated

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import AfterValidator, BaseModel, Field
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
    BindRequestContextMiddleware,
    CatchUnexpectedErrorsMiddleware,
    NoStoreCacheControlMiddleware,
)

pytestmark = pytest.mark.unit


def _reject(value: str) -> str:
    msg = "rejected"
    raise ValueError(msg)


class _LimitedInput(BaseModel):
    name: str = Field(max_length=3)
    code: Annotated[str, AfterValidator(_reject)] = "x"


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

    @app.post("/limited")
    async def limited(_: _LimitedInput) -> None:
        pass

    # The same relative order as create_app: the catch sits inside the
    # middleware whose headers every response must carry.
    app.add_middleware(CatchUnexpectedErrorsMiddleware)
    app.add_middleware(NoStoreCacheControlMiddleware)
    app.add_middleware(BindRequestContextMiddleware)
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
    assert response.json() == {
        "type": "/problems/internal-error",
        "title": "Internal Server Error",
        "status": 500,
        "code": "INTERNAL_ERROR",
    }
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
    assert response.json() == {
        "type": "/problems/internal-error",
        "title": "Internal Server Error",
        "status": 500,
        "code": "INTERNAL_ERROR",
    }
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
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.json() == {
        "type": "/problems/http-error",
        "title": HTTPStatus(status_code).phrase,
        "status": status_code,
        "code": "HTTP_ERROR",
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


def test_validation_error_carries_the_broken_limit_but_not_the_input(
    client: TestClient,
) -> None:
    response = client.post("/limited", json={"name": "toolong", "code": "secret"})

    errors = response.json()["errors"]
    by_field = {error["loc"][-1]: error for error in errors}
    assert by_field["name"]["ctx"] == {"max_length": 3}
    # A custom validator's ctx holds the exception object, which stays out.
    assert by_field["code"]["ctx"] == {}
    assert "toolong" not in response.text
    assert "secret" not in response.text


def test_well_formed_request_id_is_reused(client: TestClient) -> None:
    response = client.get("/boom", headers={"X-Request-ID": "proxy-id.42"})

    assert response.headers["X-Request-ID"] == "proxy-id.42"


@pytest.mark.parametrize("request_id", ['x" level=critical', "a" * 129, "line\tbreak"])
def test_malformed_request_id_is_replaced(client: TestClient, request_id: str) -> None:
    response = client.get("/boom", headers={"X-Request-ID": request_id})

    assert response.headers["X-Request-ID"] != request_id
    assert len(response.headers["X-Request-ID"]) == 32
